#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국토정보위성 자동 처리 스크립트
KOMPSAT L3A 데이터 지리보정 및 NDVI 계산 자동화

사용법:
    python kompsat_auto_processor.py <입력폴더경로>
    
예시:
    python kompsat_auto_processor.py "D:\\국토정보위성\\L3A_202401120060_20230316_37709024"
"""

import xml.etree.ElementTree as ET
import os
import sys
from osgeo import gdal, osr
import numpy as np
from datetime import datetime


class KompsatProcessor:
    """KOMPSAT 위성 데이터 자동 처리 클래스"""
    
    def __init__(self, input_dir):
        self.input_dir = input_dir
        self.output_dir = os.path.join(input_dir, 'ProcessedOutputs')
        self.xml_file = None
        self.bands_info = {}
        self.georef_files = {}
        
        # 출력 디렉토리 생성
        os.makedirs(self.output_dir, exist_ok=True)
        
        # PROJ 데이터 경로 설정 (Windows venv 대응)
        self._setup_proj_path()

    def _setup_proj_path(self):
        """GDAL이 proj.db를 찾을 수 있도록 환경 설정"""
        import sys
        # 후보 경로들
        candidates = []
        for p in sys.path:
            if not p or not os.path.isdir(p): continue
            
            # 1. osgeo/data/proj (site-packages 내부)
            path1 = os.path.join(p, 'osgeo', 'data', 'proj')
            if os.path.exists(os.path.join(path1, 'proj.db')):
                candidates.append(path1)
                
            # 2. PROJ_LIB 환경 변수 (이미 설정되어 있다면 최우선)
            pl = os.environ.get('PROJ_LIB')
            if pl and os.path.isdir(pl):
                candidates.insert(0, pl)

        if candidates:
            try:
                # 첫 번째 유효한 경로 사용
                search_path = candidates[0]
                osr.SetPROJSearchPaths([search_path])
                os.environ['PROJ_LIB'] = search_path # 호환성을 위해 환경 변수도 설정
            except Exception as e:
                print(f"  [경고] PROJ 경로 설정 실패: {str(e)}")
        
    def find_xml_file(self):
        """Aux.xml 파일 하나 찾기 (레거시 호환)"""
        for filename in os.listdir(self.input_dir):
            if filename.endswith('_Aux.xml'):
                self.xml_file = os.path.join(self.input_dir, filename)
                return True
        return False

    def find_xml_files(self):
        """폴더 내 모든 Aux.xml 리스트 반환"""
        xmls = []
        try:
            for filename in os.listdir(self.input_dir):
                if filename.endswith('_Aux.xml'):
                    xmls.append(os.path.join(self.input_dir, filename))
        except Exception:
            pass
        return sorted(xmls)
    
    def extract_band_info(self, root, band_tag, band_name):
        """XML에서 특정 밴드의 정보 추출"""
        band_elem = root.find(f'.//Image/{band_tag}')
        if band_elem is None:
            return None
        
        info = {
            'filename': band_elem.find('ImageFileName').text,
            'width': int(band_elem.find('.//ImageSize/Width').text),
            'height': int(band_elem.find('.//ImageSize/Height').text),
            'band_name': band_name
        }
        
        # 4개 코너 좌표 추출
        coords = band_elem.find('ImagingCoordinates')
        info['ul'] = (float(coords.find('.//UpperLeft/Longitude').text), 
                      float(coords.find('.//UpperLeft/Latitude').text))
        info['ur'] = (float(coords.find('.//UpperRight/Longitude').text), 
                      float(coords.find('.//UpperRight/Latitude').text))
        info['ll'] = (float(coords.find('.//LowerLeft/Longitude').text), 
                      float(coords.find('.//LowerLeft/Latitude').text))
        info['lr'] = (float(coords.find('.//LowerRight/Longitude').text), 
                      float(coords.find('.//LowerRight/Latitude').text))
        
        return info
    
    def parse_metadata(self):
        """XML 메타데이터 파싱"""
        print("\n" + "=" * 70)
        print("1단계: XML 메타데이터 파싱")
        print("=" * 70)

        # self.xml_file이 미리 지정되지 않았다면 첫 번째 파일을 탐색
        if not self.xml_file:
            if not self.find_xml_file():
                print("✗ 오류: Aux.xml 파일을 찾을 수 없습니다.")
                return False

        print(f"✓ XML 파일 발견: {os.path.basename(self.xml_file)}")
        
        tree = ET.parse(self.xml_file)
        root = tree.getroot()
        
        # 4개 밴드 정보 추출 (매 실행마다 초기화)
        self.bands_info = {}
        self.bands_info = {
            'Blue': self.extract_band_info(root, 'SR1', 'Blue'),
            'Green': self.extract_band_info(root, 'SR2', 'Green'),
            'Red': self.extract_band_info(root, 'SR3', 'Red'),
            'NIR': self.extract_band_info(root, 'SR4', 'NIR')
        }
        
        # 정보 출력
        for name, info in self.bands_info.items():
            if info:
                print(f"  {name:6s} 밴드: {info['filename']} ({info['width']}x{info['height']})")
        
        return True
    
    def georeference_image(self, input_file, output_file, info):
        """GCP를 사용해서 이미지 지리보정"""
        
        # GCP 생성 (픽셀 좌표, 지리 좌표)
        gcps = [
            gdal.GCP(info['ul'][0], info['ul'][1], 0, 0, 0),
            gdal.GCP(info['ur'][0], info['ur'][1], 0, info['width'], 0),
            gdal.GCP(info['ll'][0], info['ll'][1], 0, 0, info['height']),
            gdal.GCP(info['lr'][0], info['lr'][1], 0, info['width'], info['height'])
        ]
        
        # GDAL 예외 활성화
        gdal.UseExceptions()
        
        # 입력 파일 열기
        src_ds = gdal.Open(input_file)
        if src_ds is None:
            return False
        
        # GCP가 포함된 임시 VRT 파일 생성
        temp_vrt = output_file.replace('.tif', '_temp.vrt')
        
        try:
            # Translate로 GCP 추가를 위한 VRT 생성
            translate_options = gdal.TranslateOptions(
                format='VRT',
                outputSRS='EPSG:4326'
            )
            
            # GCP를 직접 Translate 단계에서 넣는 것이 더 안전함
            temp_ds = gdal.Translate(temp_vrt, src_ds, options=translate_options)
            
            if temp_ds is None:
                raise Exception(f"gdal.Translate returned None for {temp_vrt}")
            
            # SRS 정의
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)
            srs_wkt = srs.ExportToWkt()
            
            # GCP 적용
            temp_ds.SetGCPs(gcps, srs_wkt)
            temp_ds.FlushCache()
            temp_ds = None # 파일 닫기
            
        except Exception as e:
            print(f"  ✗ GDAL Translate 오류: {str(e)}")
            if os.path.exists(temp_vrt):
                try: os.remove(temp_vrt)
                except: pass
            src_ds = None
            return False
        
        # Warp로 실제 지리보정 수행
        warp_options = gdal.WarpOptions(
            format='GTiff',
            srcSRS='EPSG:4326',
            dstSRS='EPSG:5179',  # Korea2000 좌표계
            resampleAlg='cubic',
            creationOptions=['COMPRESS=LZW', 'TILED=YES']
        )
        
        gdal.Warp(output_file, temp_vrt, options=warp_options)
        
        # 임시 파일 삭제
        if os.path.exists(temp_vrt):
            os.remove(temp_vrt)
        
        src_ds = None
        return True
    
    def georeference_bands(self):
        """모든 밴드 지리보정"""
        print("\n" + "=" * 70)
        print("2단계: 지리보정 (GCP 기반)")
        print("=" * 70)
        
        for band_name, info in self.bands_info.items():
            if info is None:
                continue
            
            input_path = os.path.join(self.input_dir, info['filename'])
            output_filename = info['filename'].replace('.tif', '_georef.tif')
            output_path = os.path.join(self.output_dir, output_filename)
            
            print(f"  처리 중: {band_name} 밴드... ", end='')
            
            if self.georeference_image(input_path, output_path, info):
                self.georef_files[band_name] = output_path
                print("✓")
            else:
                print("✗")
        
        print(f"\n✓ 지리보정 완료: {len(self.georef_files)}/4 개 밴드")
        return len(self.georef_files) == 4
    
    def create_rgb_composite(self):
        """RGB 합성 이미지 생성"""
        print("\n" + "=" * 70)
        print("3단계: RGB 합성 이미지 생성")
        print("=" * 70)
        
        if 'Red' not in self.georef_files or 'Green' not in self.georef_files or 'Blue' not in self.georef_files:
            print("✗ RGB 밴드가 부족합니다.")
            return None
        
        # 출력 파일명 생성 (날짜 추출 시 안전한 루틴 사용)
        base_name = os.path.basename(self.xml_file).replace('_Aux.xml', '')
        parts = base_name.split('_')
        date_str = parts[2] if len(parts) > 2 else datetime.now().strftime('%Y%m%d')
        rgb_file = os.path.join(self.output_dir, f'RGB_Composite_{date_str}.tif')
        
        # 각 밴드 읽기
        red_ds = gdal.Open(self.georef_files['Red'])
        green_ds = gdal.Open(self.georef_files['Green'])
        blue_ds = gdal.Open(self.georef_files['Blue'])
        
        red_data = red_ds.GetRasterBand(1).ReadAsArray()
        green_data = green_ds.GetRasterBand(1).ReadAsArray()
        blue_data = blue_ds.GetRasterBand(1).ReadAsArray()
        
        # RGB 합성 이미지 생성
        driver = gdal.GetDriverByName('GTiff')
        rgb_ds = driver.Create(
            rgb_file,
            red_ds.RasterXSize,
            red_ds.RasterYSize,
            3,
            gdal.GDT_UInt16,
            options=['COMPRESS=LZW', 'TILED=YES', 'PHOTOMETRIC=RGB']
        )
        
        # 지리 정보 복사
        rgb_ds.SetGeoTransform(red_ds.GetGeoTransform())
        rgb_ds.SetProjection(red_ds.GetProjection())
        
        # 각 밴드 쓰기
        rgb_ds.GetRasterBand(1).WriteArray(red_data)
        rgb_ds.GetRasterBand(2).WriteArray(green_data)
        rgb_ds.GetRasterBand(3).WriteArray(blue_data)
        
        # 통계 계산
        for i in range(1, 4):
            rgb_ds.GetRasterBand(i).ComputeStatistics(False)
        
        # 파일 닫기
        red_ds = None
        green_ds = None
        blue_ds = None
        rgb_ds = None
        
        print(f"✓ RGB 합성 완료: {os.path.basename(rgb_file)}")
        return rgb_file
    
    def calculate_ndvi(self):
        """NDVI 계산"""
        print("\n" + "=" * 70)
        print("4단계: NDVI 계산")
        print("=" * 70)
        
        if 'Red' not in self.georef_files or 'NIR' not in self.georef_files:
            print("✗ Red 또는 NIR 밴드가 없습니다.")
            return None
        
        # 출력 파일명 생성
        base_name = os.path.basename(self.xml_file).replace('_Aux.xml', '')
        parts = base_name.split('_')
        date_str = parts[2] if len(parts) > 2 else datetime.now().strftime('%Y%m%d')
        ndvi_file = os.path.join(self.output_dir, f'NDVI_{date_str}.tif')
        
        # Red 밴드 읽기
        red_ds = gdal.Open(self.georef_files['Red'])
        red_data = red_ds.GetRasterBand(1).ReadAsArray().astype(float)
        
        # NIR 밴드 읽기
        nir_ds = gdal.Open(self.georef_files['NIR'])
        nir_data = nir_ds.GetRasterBand(1).ReadAsArray().astype(float)
        
        # NDVI 계산: (NIR - Red) / (NIR + Red)
        denominator = nir_data + red_data
        denominator[denominator == 0] = np.nan
        ndvi = (nir_data - red_data) / denominator
        
        # 통계 출력
        ndvi_min = np.nanmin(ndvi)
        ndvi_max = np.nanmax(ndvi)
        ndvi_mean = np.nanmean(ndvi)
        
        print(f"  범위: {ndvi_min:.4f} ~ {ndvi_max:.4f}")
        print(f"  평균: {ndvi_mean:.4f}")
        
        # NDVI 저장
        driver = gdal.GetDriverByName('GTiff')
        ndvi_ds = driver.Create(
            ndvi_file,
            red_ds.RasterXSize,
            red_ds.RasterYSize,
            1,
            gdal.GDT_Float32,
            options=['COMPRESS=LZW', 'TILED=YES']
        )
        
        # 지리 정보 복사
        ndvi_ds.SetGeoTransform(red_ds.GetGeoTransform())
        ndvi_ds.SetProjection(red_ds.GetProjection())
        
        # 데이터 쓰기
        ndvi_band = ndvi_ds.GetRasterBand(1)
        ndvi_band.WriteArray(ndvi)
        ndvi_band.SetNoDataValue(-9999)
        ndvi_band.ComputeStatistics(False)
        
        # 파일 닫기
        red_ds = None
        nir_ds = None
        ndvi_ds = None
        
        print(f"✓ NDVI 계산 완료: {os.path.basename(ndvi_file)}")
        return ndvi_file

    def calculate_evi(self):
        """EVI (Enhanced Vegetation Index) 계산"""
        print("\n" + "=" * 70)
        print("4-2단계: EVI 계산")
        print("=" * 70)
        
        if 'Blue' not in self.georef_files or 'Red' not in self.georef_files or 'NIR' not in self.georef_files:
            print("✗ Blue, Red 또는 NIR 밴드가 부족합니다.")
            return None
        
        # 출력 파일명 생성
        base_name = os.path.basename(self.xml_file).replace('_Aux.xml', '')
        parts = base_name.split('_')
        date_str = parts[2] if len(parts) > 2 else datetime.now().strftime('%Y%m%d')
        evi_file = os.path.join(self.output_dir, f'EVI_{date_str}.tif')
        
        # 밴드 읽기
        blue_ds = gdal.Open(self.georef_files['Blue'])
        blue_data = blue_ds.GetRasterBand(1).ReadAsArray().astype(float)
        
        red_ds = gdal.Open(self.georef_files['Red'])
        red_data = red_ds.GetRasterBand(1).ReadAsArray().astype(float)
        
        nir_ds = gdal.Open(self.georef_files['NIR'])
        nir_data = nir_ds.GetRasterBand(1).ReadAsArray().astype(float)
        
        # EVI 계산 공식: G * (NIR - Red) / (NIR + C1 * Red - C2 * Blue + L)
        # G=2.5, C1=6, C2=7.5, L=1
        G, C1, C2, L = 2.5, 6.0, 7.5, 1.0
        
        denominator = nir_data + C1 * red_data - C2 * blue_data + L
        # 0 나누기 방지
        denominator[denominator == 0] = np.nan
        
        evi = G * (nir_data - red_data) / denominator
        
        # 범위 필터링 (일반적으로 -1.0 ~ 1.0 사이, 극단적 이상치 제거)
        # evi[evi < -1.0] = -1.0
        # evi[evi > 1.0] = 1.0
        
        # 통계
        evi_min = np.nanmin(evi)
        evi_max = np.nanmax(evi)
        
        print(f"  범위: {evi_min:.4f} ~ {evi_max:.4f}")
        
        # EVI 저장
        driver = gdal.GetDriverByName('GTiff')
        evi_ds = driver.Create(
            evi_file,
            red_ds.RasterXSize,
            red_ds.RasterYSize,
            1,
            gdal.GDT_Float32,
            options=['COMPRESS=LZW', 'TILED=YES']
        )
        
        evi_ds.SetGeoTransform(red_ds.GetGeoTransform())
        evi_ds.SetProjection(red_ds.GetProjection())
        
        evi_band = evi_ds.GetRasterBand(1)
        evi_band.WriteArray(evi)
        evi_band.SetNoDataValue(-9999)
        evi_band.ComputeStatistics(False)
        
        blue_ds = red_ds = nir_ds = evi_ds = None
        
        print(f"✓ EVI 계산 완료: {os.path.basename(evi_file)}")
        return evi_file

    # ===== 모자이크/외부 파일 기반 유틸 =====
    @staticmethod
    def mosaic_raster(input_files, output_file, dst_srs='EPSG:5179', resampleAlg='cubic'):
        """여러 래스터를 하나로 모자이크 (GTiff)
        - input_files: 동일 밴드의 지리보정된 GeoTIFF 목록
        - output_file: 결과 GeoTIFF 경로
        """
        if not input_files:
            return None
        # GDAL Warp로 모자이크 수행
        warp_opts = gdal.WarpOptions(
            format='GTiff',
            dstSRS=dst_srs,
            resampleAlg=resampleAlg,
            creationOptions=['COMPRESS=LZW', 'TILED=YES']
        )
        gdal.Warp(output_file, input_files, options=warp_opts)
        return output_file if os.path.exists(output_file) else None

    @staticmethod
    def create_rgb_from_singlebands(red_file, green_file, blue_file, output_file):
        """단일밴드 파일 3개로 RGB 합성 생성"""
        if not (red_file and green_file and blue_file):
            return None
        red_ds = gdal.Open(red_file)
        green_ds = gdal.Open(green_file)
        blue_ds = gdal.Open(blue_file)
        if not red_ds or not green_ds or not blue_ds:
            return None

        red = red_ds.GetRasterBand(1).ReadAsArray()
        green = green_ds.GetRasterBand(1).ReadAsArray()
        blue = blue_ds.GetRasterBand(1).ReadAsArray()

        driver = gdal.GetDriverByName('GTiff')
        rgb_ds = driver.Create(
            output_file,
            red_ds.RasterXSize,
            red_ds.RasterYSize,
            3,
            gdal.GDT_UInt16,
            options=['COMPRESS=LZW', 'TILED=YES', 'PHOTOMETRIC=RGB']
        )
        rgb_ds.SetGeoTransform(red_ds.GetGeoTransform())
        rgb_ds.SetProjection(red_ds.GetProjection())
        rgb_ds.GetRasterBand(1).WriteArray(red)
        rgb_ds.GetRasterBand(2).WriteArray(green)
        rgb_ds.GetRasterBand(3).WriteArray(blue)
        for i in range(1, 4):
            rgb_ds.GetRasterBand(i).ComputeStatistics(False)
        red_ds = green_ds = blue_ds = None
        rgb_ds = None
        return output_file if os.path.exists(output_file) else None

    @staticmethod
    def compute_ndvi_from_files(red_file, nir_file, output_file):
        """Red/NIR 파일로 NDVI 계산 후 저장"""
        if not (red_file and nir_file):
            return None
        red_ds = gdal.Open(red_file)
        nir_ds = gdal.Open(nir_file)
        if not red_ds or not nir_ds:
            return None
        red = red_ds.GetRasterBand(1).ReadAsArray().astype(float)
        nir = nir_ds.GetRasterBand(1).ReadAsArray().astype(float)
        denom = nir + red
        denom[denom == 0] = np.nan
        ndvi = (nir - red) / denom

        driver = gdal.GetDriverByName('GTiff')
        ndvi_ds = driver.Create(
            output_file,
            red_ds.RasterXSize,
            red_ds.RasterYSize,
            1,
            gdal.GDT_Float32,
            options=['COMPRESS=LZW', 'TILED=YES']
        )
        ndvi_ds.SetGeoTransform(red_ds.GetGeoTransform())
        ndvi_ds.SetProjection(red_ds.GetProjection())
        band = ndvi_ds.GetRasterBand(1)
        band.WriteArray(ndvi)
        band.SetNoDataValue(-9999)
        band.ComputeStatistics(False)
        red_ds = nir_ds = None
        ndvi_ds = None
        return output_file if os.path.exists(output_file) else None
    
    def generate_report(self, rgb_file, ndvi_file):
        """처리 결과 보고서 생성"""
        print("\n" + "=" * 70)
        print(" 처리 완료 보고서")
        print("=" * 70)
        
        print(f"\n처리 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"입력 폴더: {os.path.basename(self.input_dir)}")
        print(f"출력 폴더: {self.output_dir}")
        
        print("\n생성된 파일:")
        print("-" * 70)
        
        file_count = 0
        for band_name, filepath in self.georef_files.items():
            if os.path.exists(filepath):
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                print(f"  • {band_name} 밴드 (지리보정): {size_mb:.2f} MB")
                file_count += 1
        
        if rgb_file and os.path.exists(rgb_file):
            size_mb = os.path.getsize(rgb_file) / (1024 * 1024)
            print(f"  • RGB 합성 이미지: {size_mb:.2f} MB")
            file_count += 1
        
        if ndvi_file and os.path.exists(ndvi_file):
            size_mb = os.path.getsize(ndvi_file) / (1024 * 1024)
            print(f"  • NDVI 분석 결과: {size_mb:.2f} MB")
            file_count += 1
        
        if 'evi_file' in locals() and evi_file and os.path.exists(evi_file):
            size_mb = os.path.getsize(evi_file) / (1024 * 1024)
            print(f"  • EVI 분석 결과: {size_mb:.2f} MB")
            file_count += 1
        
        print(f"\n✓ 총 {file_count}개 파일 생성 완료!")
        print("\n" + "=" * 70)
    
    # ========= NDVI 리포트(HTML) 유틸 =========
    @staticmethod
    def _compute_band_statistics(tif_path):
        ds = gdal.Open(tif_path)
        if ds is None:
            return None
        band = ds.GetRasterBand(1)
        # 통계 계산 (NoData는 GDAL이 자동 제외)
        stats = band.GetStatistics(True, True)
        if stats is None:
            stats = band.ComputeStatistics(False)
        if stats is None:
            return None
        minv, maxv, meanv, stdv = stats
        # 히스토그램 (근사 OK, 256 구간)
        hist = band.GetHistogram(minv, maxv, 256, True, True)
        ds = None
        return {
            'min': float(minv),
            'max': float(maxv),
            'mean': float(meanv),
            'std': float(stdv),
            'hist': hist,
        }

    @staticmethod
    def _export_quicklook_png(tif_path, out_png, width_max=1024):
        ds = gdal.Open(tif_path)
        if ds is None:
            return False
        xsize = ds.RasterXSize
        ysize = ds.RasterYSize
        ratio = min(1.0, float(width_max) / float(xsize))
        w = max(1, int(xsize * ratio))
        h = max(1, int(ysize * ratio))
        band = ds.GetRasterBand(1)
        stats = band.GetStatistics(True, True)
        if stats is None:
            stats = band.ComputeStatistics(False)
        if stats is None:
            stats = (0.0, 1.0, 0.5, 0.2)
        minv, maxv, _, _ = stats
        opts = gdal.TranslateOptions(
            format='PNG',
            width=w,
            height=h,
            scaleParams=[[minv, maxv, 0, 255]]
        )
        gdal.Translate(out_png, ds, options=opts)
        ds = None
        return os.path.exists(out_png)

    @staticmethod
    def _percentiles_from_hist(hist, minv, maxv, percentiles=(5, 25, 50, 75, 95)):
        if not hist:
            return {}
        total = float(sum(hist))
        edges = np.linspace(minv, maxv, num=len(hist)+1)
        csum = np.cumsum(hist) / total
        results = {}
        for p in percentiles:
            t = p / 100.0
            idx = np.searchsorted(csum, t)
            idx = min(max(idx, 0), len(edges)-2)
            results[p] = float(edges[idx])
        return results

    @staticmethod
    def generate_ndvi_html_report(ndvi_path, rgb_path=None, title="NDVI 결과 보고서"):
        try:
            if not os.path.exists(ndvi_path):
                return None
            out_dir = os.path.dirname(ndvi_path)
            base_name = os.path.splitext(os.path.basename(ndvi_path))[0]
            html_path = os.path.join(out_dir, f"{base_name}_Report.html")

            # 통계/히스토그램/퍼센타일
            stats = KompsatProcessor._compute_band_statistics(ndvi_path)
            if not stats:
                return None
            ptiles = KompsatProcessor._percentiles_from_hist(stats['hist'], stats['min'], stats['max'])

            # 클래스 구간 집계(표준적 임계 예시)
            classes = [
                ("< 0.0", -1.0, 0.0),
                ("0.0 - 0.2", 0.0, 0.2),
                ("0.2 - 0.4", 0.2, 0.4),
                ("0.4 - 0.6", 0.4, 0.6),
                ("0.6 - 0.8", 0.6, 0.8),
                ("> 0.8", 0.8, 2.0),
            ]
            # 히스토그램 기반 근사 집계
            hist = stats['hist']
            edges = np.linspace(stats['min'], stats['max'], num=len(hist)+1)
            class_rows = []
            total = float(sum(hist))
            for label, lo, hi in classes:
                # 구간에 해당하는 히스토그램 bin 합산
                idx_lo = np.searchsorted(edges, lo, side='left')
                idx_hi = np.searchsorted(edges, hi, side='right') - 1
                idx_lo = max(0, min(idx_lo, len(hist)-1))
                idx_hi = max(0, min(idx_hi, len(hist)-1))
                count = sum(hist[idx_lo:idx_hi+1]) if idx_hi >= idx_lo else 0
                pct = (count / total * 100.0) if total > 0 else 0.0
                class_rows.append((label, int(count), pct))

            # 퀵룩 PNG 생성
            quicklook = os.path.join(out_dir, f"{base_name}_quicklook.png")
            KompsatProcessor._export_quicklook_png(ndvi_path, quicklook)

            # HTML 작성
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            rgb_link = f"<li>RGB: {os.path.basename(rgb_path)}</li>" if rgb_path and os.path.exists(rgb_path) else ""
            rows_html = "\n".join(
                f"<tr><td>{lbl}</td><td style='text-align:right'>{cnt:,}</td><td style='text-align:right'>{pct:.2f}%</td></tr>"
                for (lbl, cnt, pct) in class_rows
            )
            ptiles_html = " ".join([f"P{int(k)}={v:.3f}" for k, v in ptiles.items()])
            html = f"""
<!doctype html>
<html lang='ko'>
<head>
  <meta charset='utf-8'/>
  <title>{title}</title>
  <style>
    body {{ font-family: 'Segoe UI', Malgun Gothic, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 0; }}
    .meta {{ color: #666; margin-bottom: 16px; }}
    table {{ border-collapse: collapse; width: 560px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 10px; }}
    th {{ background: #f5f5f5; text-align: left; }}
    .small {{ color:#666; font-size: 12px; }}
  </style>
  </head>
  <body>
    <h1>NDVI 결과 보고서</h1>
    <div class='meta'>생성 시각: {now}</div>
    <h2>개요</h2>
    <ul>
      <li>NDVI 파일: {os.path.basename(ndvi_path)}</li>
      {rgb_link}
      <li>해상도: 자동</li>
      <li>좌표계: 원본 GeoTIFF와 동일</li>
    </ul>

    <h2>통계 요약</h2>
    <p>min={stats['min']:.4f}, max={stats['max']:.4f}, mean={stats['mean']:.4f}, std={stats['std']:.4f}</p>
    <p class='small'>{ptiles_html}</p>

    <h2>NDVI 클래스 분포(근사)</h2>
    <table>
      <thead><tr><th>구간</th><th>픽셀수</th><th>비율</th></tr></thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>

    <h2>퀵룩 미리보기</h2>
    <p class='small'>QGIS 색상표(예: Turbo) 스타일은 프로젝트에서 적용하세요.</p>
    <img src='{os.path.basename(quicklook)}' alt='NDVI quicklook' style='max-width:960px;border:1px solid #ddd'/>

  </body>
</html>
"""
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return html_path
        except Exception as e:
            print(f"리포트 생성 오류: {str(e)}")
            return None

    def process(self):
        """전체 처리 실행 (폴더 내 다수 Aux.xml 지원)"""
        print("\n" + "=" * 70)
        print(" 국토정보위성 자동 처리 시작")
        print("=" * 70)
        print(f"입력 폴더: {self.input_dir}")

        xml_list = self.find_xml_files()
        if not xml_list:
            print("✗ 오류: Aux.xml 파일을 찾을 수 없습니다.")
            return False

        all_success = True
        for idx, xml_path in enumerate(xml_list, 1):
            print("\n" + "-" * 70)
            print(f"데이터셋 {idx}/{len(xml_list)}: {os.path.basename(xml_path)}")
            print("-" * 70)

            # 각 XML마다 상태 초기화
            self.xml_file = xml_path
            self.bands_info = {}
            self.georef_files = {}

            # 1. 메타데이터 파싱
            if not self.parse_metadata():
                all_success = False
                continue

            # 2. 지리보정
            if not self.georeference_bands():
                all_success = False
                continue

            # 3. RGB 합성
            rgb_file = self.create_rgb_composite()

            # 4. NDVI 계산
            ndvi_file = self.calculate_ndvi()

            # 5. 콘솔 보고 + HTML 리포트 생성
            self.generate_report(rgb_file, ndvi_file)
            if ndvi_file:
                KompsatProcessor.generate_ndvi_html_report(ndvi_file, rgb_file)

        return all_success


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python kompsat_auto_processor.py <입력폴더경로>")
        print('예시: python kompsat_auto_processor.py "D:\\국토정보위성\\L3A_202401120060_20230316_37709024"')
        sys.exit(1)
    
    input_dir = sys.argv[1]
    
    if not os.path.isdir(input_dir):
        print(f"오류: '{input_dir}' 폴더를 찾을 수 없습니다.")
        sys.exit(1)
    
    # 처리기 생성 및 실행
    processor = KompsatProcessor(input_dir)
    
    try:
        success = processor.process()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
