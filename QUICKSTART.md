# 🚀 국토정보위성 자동화 시스템 - 빠른 시작 가이드

## ✅ 완료된 작업

### 🎨 NEW! Windows GUI 추가! ✓
- **사용자 친화적인 그래픽 인터페이스**
- 마우스 클릭만으로 전체 처리 가능
- 실시간 진행 상황 표시
- 배치 처리 지원
- 색상 코딩된 로그 출력
- 멀티스레딩으로 GUI 응답성 유지

### 1. QGIS MCP를 통한 실시간 처리 ✓
- XML 메타데이터 파싱 완료
- 4개 밴드(B, G, R, NIR) 지리보정 완료
- RGB 합성 이미지 생성 완료
- NDVI 계산 완료 (범위: -1.0 ~ 0.73, 평균: 0.069)
- QGIS 프로젝트 저장 완료
- 색상 램프 적용 완료

### 2. 생성된 파일
📁 `D:\국토정보위성\L3A_202401120060_20230316_37709024\ProcessedOutputs\`
- ✅ `L3A_*_B_georef.tif` (2.27 MB) - Blue 밴드
- ✅ `L3A_*_G_georef.tif` (2.43 MB) - Green 밴드
- ✅ `L3A_*_R_georef.tif` (2.54 MB) - Red 밴드
- ✅ `L3A_*_N_georef.tif` (2.88 MB) - NIR 밴드
- ✅ `RGB_Composite_20230316.tif` (7.82 MB) - RGB 합성
- ✅ `NDVI_20230316.tif` (6.95 MB) - NDVI 분석
- ✅ `map_preview.png` (0.39 MB) - 미리보기
- ✅ `kompsat_ndvi_project.qgz` - QGIS 프로젝트

### 3. 독립 실행형 스크립트
📄 `D:\국토정보위성\`
- ✅ `kompsat_gui.py` - **Windows GUI 프로그램** 🆕
- ✅ `run_gui.bat` - **GUI 실행 파일** 🆕
- ✅ `kompsat_auto_processor.py` - 단일 폴더 처리
- ✅ `batch_process_all.py` - 배치 처리
- ✅ `run_processor.bat` - 명령줄 실행 파일
- ✅ `README.md` - 상세 문서
- ✅ `GUI_GUIDE.md` - GUI 사용 가이드 🆕

---

## 🎯 사용 방법

### 방법 1: GUI 실행 (가장 쉬움! 🆕 추천!)
```
run_gui.bat 파일을 더블클릭
```
→ 그래픽 인터페이스가 열립니다!
- 📁 폴더 선택 버튼 클릭
- ⚙️ 옵션 체크
- 🚀 처리 시작 버튼 클릭

### 방법 2: 명령줄 배치 실행
```
run_processor.bat 파일을 더블클릭
```

### 방법 3: 명령줄 실행
```bash
# 단일 폴더
python kompsat_auto_processor.py "D:\국토정보위성\L3A_202401120060_20230316_37709024"

# 배치 처리 (여러 폴더)
python batch_process_all.py "D:\국토정보위성"
```

### 방법 3: QGIS MCP (이미 완료됨)
QGIS에서 MCP 서버를 통해 실시간으로 처리
✅ 현재 프로젝트가 이미 로드되어 있습니다!

---

## 📊 처리 결과 확인

### QGIS에서 확인
1. QGIS 열기
2. 프로젝트 열기: `kompsat_ndvi_project.qgz`
3. 레이어 패널에서 각 레이어 확인

### 파일 탐색기에서 확인
`ProcessedOutputs` 폴더 열기

---

## 🎨 NDVI 해석

| 색상 | NDVI 값 | 의미 |
|------|---------|------|
| 🟤 갈색 | -1.0 ~ -0.1 | 물, 그림자, 나지, 도시 |
| 🟡 노랑 | 0.0 ~ 0.2 | 식생 낮음 |
| 🟢 연두 | 0.2 ~ 0.4 | 식생 중간 |
| 🟩 녹색 | 0.4 ~ 0.8 | 식생 높음 |
| 🌲 진한 녹색 | 0.8 ~ 1.0 | 식생 매우 높음 |

**현재 데이터 통계:**
- 범위: -1.0 ~ 0.73
- 평균: 0.069 (낮은 식생 밀도)

---

## 🔄 다른 날짜/영역 데이터 처리

### 단일 폴더
```bash
python kompsat_auto_processor.py "새폴더경로"
```

### 여러 폴더 일괄 처리
```bash
python batch_process_all.py "D:\국토정보위성"
```
→ 모든 L3A 폴더를 자동으로 찾아서 처리

---

## 🛠️ 커스터마이징

### NDVI 색상 변경
`kompsat_auto_processor.py` 파일에서 색상 정의 수정

### 다른 좌표계 사용
```python
dstSRS='EPSG:4326'  # WGS84
dstSRS='EPSG:3857'  # Web Mercator
```

### 다른 인덱스 계산 (예: NDWI)
```python
# 물 지수
ndwi = (green_data - nir_data) / (green_data + nir_data)
```

---

## 📋 체크리스트

- [x] XML 메타데이터 파싱
- [x] 4개 밴드 지리보정
- [x] RGB 합성
- [x] NDVI 계산
- [x] QGIS 프로젝트 생성
- [x] 색상 시각화
- [x] 독립 실행형 스크립트
- [x] 배치 처리 스크립트
- [x] 문서화

---

## 🎉 완료!

모든 자동화가 완료되었습니다!

### 지금 할 수 있는 것:
1. ✅ QGIS에서 결과 확인 (이미 열려있음)
2. ✅ 다른 날짜 데이터 자동 처리
3. ✅ 배치 처리로 여러 폴더 한번에 처리
4. ✅ 스크립트 커스터마이징

### 파일 위치:
- 📁 스크립트: `D:\국토정보위성\*.py`
- 📁 결과 파일: `ProcessedOutputs\` 폴더
- 📁 QGIS 프로젝트: `kompsat_ndvi_project.qgz`

---

## 💡 추가 아이디어

### 향후 개선 사항:
1. Cloud Mask 적용 (CloudMapHigh/Low.tif 활용)
2. NoData 마스킹
3. 다중 시기 NDVI 비교 (시계열 분석)
4. 자동 보고서 생성 (PDF)
5. Web Map 생성 (Leaflet/OpenLayers)

### 다른 식생 지수:
- **EVI** (Enhanced Vegetation Index)
- **SAVI** (Soil-Adjusted Vegetation Index)
- **NDWI** (Normalized Difference Water Index)

---

**질문이나 문제가 있으면 README.md를 참고하세요!** 📚
