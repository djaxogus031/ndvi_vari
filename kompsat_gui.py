#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국토정보위성 자동 처리 GUI
사용자 친화적인 Windows 인터페이스

실행: python kompsat_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import os
import os
import threading
from datetime import datetime
import subprocess
import shutil
import glob

import configparser
# GDAL 확인
try:
    # 런타임에 venv의 site-packages를 명시적으로 sys.path에 확인 (런처 미경유 시 대비)
    import sys
    import os
    from kompsat_auto_processor import KompsatProcessor
    GDAL_AVAILABLE = True
except ImportError as e:
    import traceback
    GDAL_AVAILABLE = False
    GDAL_ERROR = f"{str(e)}\n{traceback.format_exc()}"


class KompsatGUI:
    """KOMPSAT 처리 GUI 클래스"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("국토정보위성 자동 처리 시스템")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 변수
        self.selected_folders = []
        self.is_processing = False
        self.qgis_path_var = tk.StringVar()
        self.settings_path = os.path.join(os.path.dirname(__file__), 'kompsat_settings.ini')
        self.load_settings()
        
        # UI 구성
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성"""
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 타이틀
        title_label = ttk.Label(
            main_frame, 
            text="🛰️ 국토정보위성 자동 처리 시스템",
            font=("맑은 고딕", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # === 입력 섹션 ===
        input_frame = ttk.LabelFrame(main_frame, text="📁 입력 폴더 선택", padding="10")
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 단일 폴더 선택
        ttk.Label(input_frame, text="단일 폴더:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.single_folder_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.single_folder_var, width=60).grid(
            row=0, column=1, padx=5, pady=5
        )
        ttk.Button(input_frame, text="찾아보기", command=self.browse_single_folder).grid(
            row=0, column=2, padx=5, pady=5
        )
        
        # 배치 처리 (루트 폴더)
        ttk.Label(input_frame, text="배치 처리 (루트):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.batch_folder_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.batch_folder_var, width=60).grid(
            row=1, column=1, padx=5, pady=5
        )
        ttk.Button(input_frame, text="찾아보기", command=self.browse_batch_folder).grid(
            row=1, column=2, padx=5, pady=5
        )
        
        # === 옵션 섹션 ===
        options_frame = ttk.LabelFrame(main_frame, text="⚙️ 처리 옵션", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 체크박스 옵션
        self.create_rgb_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, 
            text="RGB 합성 이미지 생성",
            variable=self.create_rgb_var
        ).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.create_ndvi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="NDVI 계산",
            variable=self.create_ndvi_var
        ).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        self.create_evi_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="EVI 계산",
            variable=self.create_evi_var
        ).grid(row=0, column=2, sticky=tk.W, padx=5)
        
        self.open_qgis_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="처리 후 QGIS 열기",
            variable=self.open_qgis_var
        ).grid(row=0, column=3, sticky=tk.W, padx=5)

        # 모자이크 옵션
        self.mosaic_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="여러 장면 모자이크(R/G/B/N) 후 NDVI",
            variable=self.mosaic_var
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(8,0))

        # QGIS 실행 파일 경로 설정
        ttk.Label(options_frame, text="QGIS 실행 파일:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=(8,0))
        ttk.Entry(options_frame, textvariable=self.qgis_path_var, width=60).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=(8,0))
        ttk.Button(options_frame, text="찾아보기", command=self.browse_qgis_exe).grid(row=2, column=2, padx=5, pady=(8,0))
        
        # === 실행 버튼 ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.process_button = ttk.Button(
            button_frame,
            text="🚀 처리 시작",
            command=self.start_processing,
            width=20
        )
        self.process_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="⏹️ 중지",
            command=self.stop_processing,
            state=tk.DISABLED,
            width=20
        )
        self.stop_button.grid(row=0, column=1, padx=5)
        
        ttk.Button(
            button_frame,
            text="📂 출력 폴더 열기",
            command=self.open_output_folder,
            width=20
        ).grid(row=0, column=2, padx=5)
        
        # === 진행 상태 ===
        progress_frame = ttk.LabelFrame(main_frame, text="📊 진행 상태", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="대기 중...", foreground="blue")
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        # === 로그 출력 ===
        log_frame = ttk.LabelFrame(main_frame, text="📝 처리 로그", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=100,
            height=20,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 로그 컬러 태그
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("info", foreground="blue")
        
        # === 하단 정보 ===
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        ttk.Label(
            info_frame,
            text="v1.0.0 | GitHub Copilot | 2025",
            font=("맑은 고딕", 8)
        ).grid(row=0, column=0, sticky=tk.W)
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 초기 로그
        self.log("국토정보위성 자동 처리 시스템이 시작되었습니다.", "info")
        
        # GDAL 확인
        if not GDAL_AVAILABLE:
            self.log("", "error")
            self.log("⚠️ 경고: GDAL 라이브러리를 찾을 수 없습니다.", "error")
            self.log(f"오류: {GDAL_ERROR}", "error")
            self.log("", "error")
            self.log("GDAL 설치 방법:", "warning")
            self.log("  1. pip install gdal", "warning")
            self.log("  또는", "warning")
            self.log("  2. https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal", "warning")
            self.log("     에서 whl 파일 다운로드 후 설치", "warning")
            self.log("", "warning")
            self.process_button.config(state=tk.DISABLED)
            messagebox.showerror(
                "오류",
                "GDAL 라이브러리가 설치되어 있지 않습니다.\n\n"
                "설치 방법:\n"
                "1. 명령 프롬프트(cmd) 실행\n"
                "2. pip install gdal 입력\n\n"
                "또는\n\n"
                "https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal\n"
                "에서 whl 파일 다운로드 후:\n"
                "pip install [다운로드한파일명].whl"
            )
        else:
            self.log("✓ GDAL 라이브러리 확인 완료", "success")
            self.log("폴더를 선택하고 '처리 시작' 버튼을 클릭하세요.", "info")
        
        # 종료 시 설정 저장
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        try:
            self.save_settings()
        finally:
            self.root.destroy()

    def load_settings(self):
        cfg = configparser.ConfigParser()
        if os.path.exists(self.settings_path):
            try:
                cfg.read(self.settings_path, encoding='utf-8')
                q = cfg.get('qgis', 'exe_path', fallback='')
                if q:
                    self.qgis_path_var.set(q)
            except Exception:
                pass

    def save_settings(self):
        try:
            cfg = configparser.ConfigParser()
            cfg['qgis'] = {
                'exe_path': self.qgis_path_var.get().strip()
            }
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                cfg.write(f)
        except Exception:
            pass

    def browse_qgis_exe(self):
        path = filedialog.askopenfilename(
            title="QGIS 실행 파일 선택",
            filetypes=[
                ("QGIS 실행 파일", "qgis*.exe"),
                ("실행 파일", "*.exe"),
                ("모든 파일", "*.*")
            ]
        )
        if path:
            self.qgis_path_var.set(path)
            self.save_settings()
        
    def browse_single_folder(self):
        """단일 폴더 선택"""
        folder = filedialog.askdirectory(title="처리할 폴더 선택 (*_Aux.xml 포함)")
        if folder:
            self.single_folder_var.set(folder)
            self.log(f"단일 폴더 선택: {folder}", "info")
            
    def browse_batch_folder(self):
        """배치 처리 루트 폴더 선택"""
        folder = filedialog.askdirectory(title="여러 대상 폴더가 있는 루트 폴더 선택 (*_Aux.xml 탐지)")
        if folder:
            self.batch_folder_var.set(folder)
            # 대상 폴더 찾기
            found_folders = self.find_kompsat_folders(folder)
            self.log(f"배치 폴더 선택: {folder}", "info")
            self.log(f"발견된 처리 대상 폴더: {len(found_folders)}개", "info")
            for f in found_folders:
                self.log(f"  • {os.path.basename(f)}", "info")
    
    def find_kompsat_folders(self, root_dir):
        """*_Aux.xml 이 있는 폴더 자동 탐지 (루트 포함, 하위 1단계)
        - 폴더명이 L3A로 시작할 필요 없음
        """
        folders = []
        try:
            # 루트 자체가 대상인지
            if any(fn.lower().endswith('_aux.xml') for fn in os.listdir(root_dir)):
                folders.append(root_dir)
            # 하위 1단계
            for item in os.listdir(root_dir):
                item_path = os.path.join(root_dir, item)
                if not os.path.isdir(item_path):
                    continue
                try:
                    if any(fn.lower().endswith('_aux.xml') for fn in os.listdir(item_path)):
                        folders.append(item_path)
                except Exception:
                    continue
        except Exception as e:
            self.log(f"폴더 검색 오류: {str(e)}", "error")
        # 중복 제거 및 정렬
        return sorted(list(set(folders)))
    
    def apply_qgis_style(self, tif_path):
        """TIFF 파일 옆에 스타일 파일(.qml)을 복사하여 QGIS에서 자동 적용되도록 함"""
        if not tif_path or not os.path.exists(tif_path):
            return
            
        # 파일 타입(NDVI/EVI/GNDVI)에 따른 전용 스타일 우선 탐색
        base_name_lower = os.path.basename(tif_path).lower()
        if 'evi' in base_name_lower:
            style_cands = ['evi_스타일.qml', '관악산_스타일.qml']
        elif 'gndvi' in base_name_lower:
            style_cands = ['gndvi_스타일.qml', '관악산_스타일.qml']
        else:
            style_cands = ['ndvi_스타일.qml', '관악산_스타일.qml']
            
        style_src = None
        for cand in style_cands:
            p = os.path.join(os.path.dirname(__file__), cand)
            if os.path.exists(p):
                style_src = p
                break
                
        if style_src:
            try:
                style_dst = tif_path.replace('.tif', '.qml')
                shutil.copy2(style_src, style_dst)
            except Exception as e:
                self.log(f"스타일 복사 실패: {str(e)}", "warning")
    
    def log(self, message, level="info"):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message, level)
        self.log_text.see(tk.END)
        self.log_text.update()
        
    def update_status(self, message, progress=None):
        """상태 업데이트"""
        self.status_label.config(text=message)
        if progress is not None:
            self.progress_var.set(progress)
        self.root.update()
        
    def start_processing(self):
        """처리 시작"""
        if self.is_processing:
            return
        
        # GDAL 확인
        if not GDAL_AVAILABLE:
            messagebox.showerror(
                "오류",
                "GDAL 라이브러리가 설치되어 있지 않습니다.\n"
                "먼저 GDAL을 설치해주세요."
            )
            return
        
        # 입력 검증
        single_folder = self.single_folder_var.get().strip()
        batch_folder = self.batch_folder_var.get().strip()
        
        if not single_folder and not batch_folder:
            messagebox.showwarning("경고", "처리할 폴더를 선택해주세요.")
            return
        
        # 처리할 폴더 목록 생성
        folders = []
        if single_folder:
            if not os.path.isdir(single_folder):
                messagebox.showerror("오류", f"폴더를 찾을 수 없습니다:\n{single_folder}")
                return
            folders.append(single_folder)
        
        if batch_folder:
            found = self.find_kompsat_folders(batch_folder)
            if not found:
                messagebox.showwarning("경고", f"처리 대상 폴더(*_Aux.xml 포함)를 찾을 수 없습니다:\n{batch_folder}")
                return
            folders.extend(found)
        
        # 중복 제거
        folders = list(set(folders))
        
        if not folders:
            messagebox.showwarning("경고", "처리할 폴더가 없습니다.")
            return
        
        # 확인 대화상자
        if len(folders) > 1:
            response = messagebox.askyesno(
                "확인",
                f"{len(folders)}개의 폴더를 처리하시겠습니까?\n\n" +
                "\n".join([f"• {os.path.basename(f)}" for f in folders[:5]]) +
                (f"\n... 외 {len(folders)-5}개" if len(folders) > 5 else "")
            )
            if not response:
                return
        
        # UI 상태 변경
        self.is_processing = True
        self.process_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        
        # 별도 스레드에서 처리
        self.processing_thread = threading.Thread(
            target=self.process_folders,
            args=(folders,),
            daemon=True
        )
        self.processing_thread.start()
        
    def process_folders(self, folders):
        """폴더 처리 (별도 스레드)"""
        try:
            self.log("=" * 70, "info")
            self.log("처리 시작", "info")
            self.log("=" * 70, "info")
            
            total_folders = len(folders)
            # 모자이크용 밴드별 파일 누적
            mosaic_bands = { 'Red': [], 'Green': [], 'Blue': [], 'NIR': [] }
            datasets_total = 0
            success_count = 0
            failed_count = 0
            
            for i, folder in enumerate(folders, 1):
                if not self.is_processing:
                    self.log("사용자에 의해 중지되었습니다.", "warning")
                    break
                
                folder_name = os.path.basename(folder)
                self.log(f"\n[{i}/{total_folders}] {folder_name}", "info")
                self.update_status(f"처리 중: {folder_name}", (i-1) / total_folders * 100)
                
                try:
                    # 폴더 내 모든 *_Aux.xml 처리
                    xml_list = [
                        os.path.join(folder, f)
                        for f in os.listdir(folder)
                        if f.lower().endswith('_aux.xml')
                    ]
                    xml_list.sort()

                    if not xml_list:
                        raise Exception("*_Aux.xml 파일을 찾을 수 없습니다.")

                    datasets_total += len(xml_list)

                    for j, xml_path in enumerate(xml_list, 1):
                        ds_name = os.path.basename(xml_path)
                        self.log(f"  ─ 데이터셋 {j}/{len(xml_list)}: {ds_name}", "info")

                        # 처리기 생성 (데이터셋별 신규 인스턴스)
                        processor = KompsatProcessor(folder)
                        processor.xml_file = xml_path  # 지정된 XML 사용

                        # 메타데이터 파싱
                        self.log("    • XML 메타데이터 파싱...", "info")
                        if not processor.parse_metadata():
                            raise Exception("메타데이터 파싱 실패")

                        # 지리보정
                        self.log("    • 지리보정 수행...", "info")
                        if not processor.georeference_bands():
                            raise Exception("지리보정 실패")

                        # 모자이크용 파일 누적
                        for bname, fpath in processor.georef_files.items():
                            if bname in mosaic_bands and os.path.exists(fpath):
                                mosaic_bands[bname].append(fpath)

                        # RGB 합성
                        if self.create_rgb_var.get():
                            self.log("    • RGB 합성 이미지 생성...", "info")
                            processor.create_rgb_composite()

                        # NDVI 계산
                        if self.create_ndvi_var.get():
                            self.log("    • NDVI 계산...", "info")
                            ndvi_file = processor.calculate_ndvi()
                            self.apply_qgis_style(ndvi_file)

                        # EVI 계산
                        if self.create_evi_var.get():
                            self.log("    • EVI 계산...", "info")
                            evi_file = processor.calculate_evi()
                            self.apply_qgis_style(evi_file)

                        self.log("    ✓ 완료!", "success")
                        success_count += 1
                    
                except Exception as e:
                    self.log(f"  ✗ 오류: {str(e)}", "error")
                    failed_count += 1
            
            # 완료
            self.update_status("처리 완료", 100)
            self.log("\n" + "=" * 70, "info")
            self.log("처리 완료", "success")
            self.log("=" * 70, "info")
            summary_total = datasets_total if datasets_total else total_folders
            self.log(f"전체 데이터셋: {summary_total}개 | 성공: {success_count}개 | 실패: {failed_count}개", "info")

            # 모자이크 처리 (선택 시)
            if self.mosaic_var.get():
                try:
                    self.log("\n모자이크 처리 시작", "info")
                    # 출력 디렉터리 결정
                    if len(folders) == 1:
                        mosaic_out = os.path.join(folders[0], "ProcessedOutputs", "Mosaic")
                    else:
                        base_dir = os.path.dirname(folders[0])
                        mosaic_out = os.path.join(base_dir, "ProcessedOutputs_Mosaic")
                    os.makedirs(mosaic_out, exist_ok=True)

                    # 밴드별 모자이크
                    from kompsat_auto_processor import KompsatProcessor as KP
                    red_mos = green_mos = blue_mos = nir_mos = None

                    if mosaic_bands['Red']:
                        self.log(f"  • Red 모자이크: {len(mosaic_bands['Red'])}장", "info")
                        red_mos = KP.mosaic_raster(mosaic_bands['Red'], os.path.join(mosaic_out, 'Mosaic_Red.tif'))
                    if mosaic_bands['Green']:
                        self.log(f"  • Green 모자이크: {len(mosaic_bands['Green'])}장", "info")
                        green_mos = KP.mosaic_raster(mosaic_bands['Green'], os.path.join(mosaic_out, 'Mosaic_Green.tif'))
                    if mosaic_bands['Blue']:
                        self.log(f"  • Blue 모자이크: {len(mosaic_bands['Blue'])}장", "info")
                        blue_mos = KP.mosaic_raster(mosaic_bands['Blue'], os.path.join(mosaic_out, 'Mosaic_Blue.tif'))
                    if mosaic_bands['NIR']:
                        self.log(f"  • NIR 모자이크: {len(mosaic_bands['NIR'])}장", "info")
                        nir_mos = KP.mosaic_raster(mosaic_bands['NIR'], os.path.join(mosaic_out, 'Mosaic_NIR.tif'))

                    # RGB 합성(모자이크 결과)
                    if red_mos and green_mos and blue_mos and self.create_rgb_var.get():
                        self.log("  • 모자이크 RGB 합성 생성", "info")
                        KP.create_rgb_from_singlebands(red_mos, green_mos, blue_mos, os.path.join(mosaic_out, 'Mosaic_RGB.tif'))

                    # NDVI(모자이크 결과)
                    ndvi_mos = None
                    if red_mos and nir_mos and self.create_ndvi_var.get():
                        self.log("  • 모자이크 NDVI 계산", "info")
                        ndvi_mos = KP.compute_ndvi_from_files(red_mos, nir_mos, os.path.join(mosaic_out, 'Mosaic_NDVI.tif'))
                        # 모자이크 NDVI 스타일 적용
                        self.apply_qgis_style(ndvi_mos)

                    # EVI(모자이크 결과)
                    if red_mos and nir_mos and blue_mos and self.create_evi_var.get():
                        self.log("  • 모자이크 EVI 계산", "info")
                        # 0.5.4 버전 이상의 processor가 필요하지만 위에서 정의된 KP를 활용
                        try:
                            # KompsatProcessor 인스턴스를 하나 만들어서 정적 메서드가 아닌 인스턴스 메서드를 활용하거나
                            # 임시로 인스턴스를 생성
                            temp_proc = KP(folders[0])
                            temp_proc.georef_files = {
                                'Red': red_mos, 'NIR': nir_mos, 'Blue': blue_mos, 'Green': green_mos
                            }
                            temp_proc.output_dir = mosaic_out
                            # 파일명을 Mosaic_EVI.tif로 강제하기 위해 _Aux.xml 대신 더미 경로 설정 후 메서드 실행보다는 
                            # 수동 호출이 안전할 수 있음. 하지만 여기서는 calculate_evi 로직을 재사용.
                            # (단, calculate_evi 내부에서 base_name을 XML에서 추출하므로 Mosaic에서는 별도 로직 필요)
                            
                            # Mosaic을 위한 EVI 계산 직접 구현 (calculate_evi 참고)
                            G, C1, C2, L = 2.5, 6.0, 7.5, 1.0
                            r_ds = gdal.Open(red_mos); r_arr = r_ds.GetRasterBand(1).ReadAsArray().astype(float)
                            n_ds = gdal.Open(nir_mos); n_arr = n_ds.GetRasterBand(1).ReadAsArray().astype(float)
                            b_ds = gdal.Open(blue_mos); b_arr = b_ds.GetRasterBand(1).ReadAsArray().astype(float)
                            den = n_arr + C1 * r_arr - C2 * b_arr + L
                            den[den == 0] = np.nan
                            evi_arr = G * (n_arr - r_arr) / den
                            out_p = os.path.join(mosaic_out, 'Mosaic_EVI.tif')
                            drv = gdal.GetDriverByName('GTiff')
                            out_ds = drv.Create(out_p, r_ds.RasterXSize, r_ds.RasterYSize, 1, gdal.GDT_Float32, ['COMPRESS=LZW', 'TILED=YES'])
                            out_ds.SetGeoTransform(r_ds.GetGeoTransform()); out_ds.SetProjection(r_ds.GetProjection())
                            out_ds.GetRasterBand(1).WriteArray(evi_arr); out_ds.GetRasterBand(1).SetNoDataValue(-9999)
                            out_ds = r_ds = n_ds = b_ds = None
                            # 모자이크 EVI 스타일 적용
                            self.apply_qgis_style(out_p)
                        except Exception as ee:
                            self.log(f"  • 모자이크 EVI 계산 실패: {str(ee)}", "error")

                    # NDVI HTML 리포트 생성
                    try:
                        if ndvi_mos:
                            KP.generate_ndvi_html_report(ndvi_mos, red_mos and green_mos and blue_mos and os.path.join(mosaic_out, 'Mosaic_RGB.tif'))
                    except Exception as _:
                        pass

                    self.log(f"모자이크 출력 폴더: {mosaic_out}", "success")
                except Exception as me:
                    self.log(f"모자이크 처리 오류: {str(me)}", "error")
            
            # 완료 메시지
            messagebox.showinfo(
                "완료",
                f"처리가 완료되었습니다!\n\n"
                f"전체 데이터셋: {summary_total}개\n"
                f"성공: {success_count}개\n"
                f"실패: {failed_count}개"
            )
            
            # QGIS 열기
            if self.open_qgis_var.get() and success_count > 0:
                self.open_qgis_project(folders[0])
            
        except Exception as e:
            self.log(f"\n치명적 오류: {str(e)}", "error")
            messagebox.showerror("오류", f"처리 중 오류가 발생했습니다:\n{str(e)}")
        
        finally:
            # UI 상태 복원
            self.is_processing = False
            self.process_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.update_status("대기 중...", 0)
    
    def stop_processing(self):
        """처리 중지"""
        if self.is_processing:
            response = messagebox.askyesno("확인", "처리를 중지하시겠습니까?")
            if response:
                self.is_processing = False
                self.log("\n중지 요청됨...", "warning")
    
    def open_output_folder(self):
        """출력 폴더 열기"""
        single_folder = self.single_folder_var.get().strip()
        batch_folder = self.batch_folder_var.get().strip()
        
        folder = single_folder if single_folder else batch_folder
        
        if folder and os.path.isdir(folder):
            output_dir = os.path.join(folder, "ProcessedOutputs")
            if os.path.isdir(output_dir):
                os.startfile(output_dir)
            else:
                messagebox.showinfo("안내", "아직 출력 폴더가 생성되지 않았습니다.\n처리를 먼저 실행해주세요.")
        else:
            messagebox.showwarning("경고", "폴더를 먼저 선택해주세요.")
    
    def find_qgis_executable(self):
        """Windows에서 QGIS 실행 파일 위치 탐색"""
        # 1. 사용자가 지정한 경로 우선
        user_path = self.qgis_path_var.get().strip()
        if user_path and os.path.exists(user_path):
            return user_path
        
        resolved = []
        # 2. PATH 시도
        qgis_in_path = shutil.which('qgis')
        if qgis_in_path:
            resolved.append(qgis_in_path)
        
        candidates = []
        # 3. 일반적인 설치 경로들 (우선순위: LTR/최신 버전 > 구버전)
        default_bases = [
            os.environ.get('ProgramFiles', r'C:\Program Files'),
            os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
            r"C:\OSGeo4W64", 
            r"C:\OSGeo4W"
        ]
        
        for base in default_bases:
            if not os.path.isdir(base):
                continue
            
            # QGIS 폴더들 찾기 (QGIS 3.40, 3.34 등 패턴 매칭)
            qgis_dirs = glob.glob(os.path.join(base, 'QGIS*'))
            # 역순 정렬하여 최신 버전이 먼저 오도록 함
            for q_dir in sorted(qgis_dirs, reverse=True):
                # .bat (런처) 우선
                for pattern in ['bin/qgis*.bat', 'qgis*.bat']:
                    candidates.extend(glob.glob(os.path.join(q_dir, pattern)))
                # .exe
                for pattern in ['bin/qgis-ltr-bin.exe', 'bin/qgis.exe', 'bin/qgis-bin.exe']:
                    candidates.extend(glob.glob(os.path.join(q_dir, pattern)))

            # OSGeo4W 루트 bin 폴더
            for pattern in ['bin/qgis*.bat', 'bin/qgis-ltr-bin.exe', 'bin/qgis.exe']:
                candidates.extend(glob.glob(os.path.join(base, pattern)))

        # 중복 제거 및 존재 확인
        seen = set()
        for c in candidates:
            cl = os.path.normpath(c).lower()
            if cl in seen:
                continue
            seen.add(cl)
            if os.path.exists(c):
                resolved.append(os.path.normpath(c))
        
        # 설정된 경로가 검색 결과에 포함되도록 함
        return resolved[0] if resolved else None

    def open_qgis_project(self, folder):
        """QGIS로 결과 열기: 프로젝트 없으면 레이어 파일로 열기 시도"""
        try:
            processed_dir = os.path.join(folder, "ProcessedOutputs")
            qgz_file = os.path.join(processed_dir, "kompsat_ndvi_project.qgz")
            
            # EVI가 선택된 경우, 기존 프로젝트(NDVI 전용일 가능성 높음) 대신 개별 파일로 열기 강제
            force_layers = self.create_evi_var.get()
            
            if os.path.exists(qgz_file) and not force_layers:
                os.startfile(qgz_file)
                return

            # 프로젝트가 없으면 레이어 직접 열기 시도
            mosaic_dir = os.path.join(processed_dir, 'Mosaic')
            layers = []
            # 선호 순서: RGB (바닥) > NDVI > EVI (맨 위)
            for name in ['Mosaic_RGB.tif', 'Mosaic_NDVI.tif', 'Mosaic_EVI.tif']:
                p = os.path.join(mosaic_dir, name)
                if os.path.exists(p):
                    layers.append(p)

            if not layers:
                self.log("모자이크 레이어(Mosaic_NDVI/Mosaic_RGB)를 찾을 수 없습니다.", "warning")
                return

            exe = self.find_qgis_executable()
            if exe:
                try:
                    self.log(f"QGIS 실행 파일: {exe}", "info")
                    # 리스트 형태로 전달하는 것이 공백 포함 경로 대처에 유리
                    cmd = [exe] + layers
                    if exe.lower().endswith('.bat'):
                        # .bat 파일은 shell=True 또는 cmd /c 이용
                        subprocess.Popen(cmd, shell=True)
                    else:
                        subprocess.Popen(cmd)
                    self.log("QGIS 실행 요청 완료", "info")
                    return
                except Exception as se:
                    self.log(f"QGIS 실행 실패: {str(se)}", "error")

            # 실행 파일을 못 찾으면 일단 첫 번째 레이어만 OS 기본 연결로 연다
            try:
                os.startfile(layers[0])
                self.log("QGIS 실행 파일을 찾지 못해 기본 연결로 열었습니다.", "warning")
            except Exception:
                self.log("QGIS 실행 파일을 찾을 수 없습니다.", "error")
        except Exception as e:
            self.log(f"QGIS 열기 오류: {str(e)}", "error")


def main():
    """메인 함수"""
    root = tk.Tk()
    app = KompsatGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
