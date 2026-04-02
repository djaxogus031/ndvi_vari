import rasterio
import numpy as np
import matplotlib.pyplot as plt
import os

def process_vegetation_indices(base_path):
    for item in os.listdir(base_path):
        folder_path = os.path.join(base_path, item)
        if os.path.isdir(folder_path):
            print(f"\n📂 '{item}' 폴더 분석 중 (NDVI & VARI)...")
            
            # 파일 초기화
            r_file = g_file = b_file = n_file = None
            
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    if f.endswith('R.tif'): r_file = os.path.join(root, f)
                    elif f.endswith('G.tif'): g_file = os.path.join(root, f)
                    elif f.endswith('B.tif'): b_file = os.path.join(root, f)
                    elif f.endswith('N.tif'): n_file = os.path.join(root, f)

            # VARI 분석 (R, G, B 필요) 및 NDVI 분석 (R, N 필요)
            if all([r_file, g_file, b_file, n_file]):
                try:
                    with rasterio.open(r_file) as src:
                        meta = src.meta
                        r = src.read(1).astype('float32')
                    with rasterio.open(g_file) as src:
                        g = src.read(1, out_shape=(meta['count'], meta['height'], meta['width'])).astype('float32')
                    with rasterio.open(b_file) as src:
                        b = src.read(1, out_shape=(meta['count'], meta['height'], meta['width'])).astype('float32')
                    with rasterio.open(n_file) as src:
                        n = src.read(1, out_shape=(meta['count'], meta['height'], meta['width'])).astype('float32')

                    np.seterr(divide='ignore', invalid='ignore')

                    # 1. NDVI 계산
                    ndvi = (n - r) / (n + r)
                    
                    # 2. VARI 계산 (가점 포인트!)
                    # 공식: (Green - Red) / (Green + Red - Blue)
                    vari = (g - r) / (g + r - b)

                    # 결과 시각화 (3분할: NDVI, VARI, 통계)
                    fig, ax = plt.subplots(1, 3, figsize=(18, 5))
                    
                    # NDVI 지도
                    im1 = ax[0].imshow(ndvi, cmap='RdYlGn', vmin=-1, vmax=1)
                    ax[0].set_title(f'NDVI Map\n({item})')
                    fig.colorbar(im1, ax=ax[0])

                    # VARI 지도
                    im2 = ax[1].imshow(vari, cmap='YlGn', vmin=-1, vmax=1)
                    ax[1].set_title(f'VARI Map (Visible Only)')
                    fig.colorbar(im2, ax=ax[1])

                    # 히스토그램 비교
                    ax[2].hist(ndvi.flatten(), bins=50, color='green', alpha=0.5, label='NDVI', range=(-1,1))
                    ax[2].hist(vari.flatten(), bins=50, color='blue', alpha=0.5, label='VARI', range=(-1,1))
                    ax[2].set_title('Index Distribution')
                    ax[2].legend()

                    plt.tight_layout()
                    output_path = os.path.join(folder_path, f"Final_Analysis_{item}.png")
                    plt.savefig(output_path)
                    plt.close()
                    
                    print(f"✅ {item} 분석 완료! (NDVI & VARI 생성됨)")
                except Exception as e:
                    print(f"❌ {item} 에러: {e}")
            else:
                print(f"⚠️ {item} 폴더에 필요한 밴드(R,G,B,N)가 부족합니다.")

current_dir = os.getcwd()
process_vegetation_indices(current_dir)