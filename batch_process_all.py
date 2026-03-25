#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국토정보위성 배치 처리 스크립트
여러 폴더를 한번에 처리

사용법:
    python batch_process_all.py <루트폴더경로>
    
예시:
    python batch_process_all.py "D:\\국토정보위성"
"""

import os
import sys
from kompsat_auto_processor import KompsatProcessor
from datetime import datetime


def find_kompsat_folders(root_dir):
    """보조 XML(*_Aux.xml)이 존재하는 폴더를 자동 탐지

    - 폴더명이 L3A로 시작하지 않아도 됨
    - root_dir 자체가 대상일 수도 있고, 하위 1단계 폴더를 검사
    """
    folders = []

    # root_dir 자체가 대상인지 확인
    try:
        if any(fn.lower().endswith('_aux.xml') for fn in os.listdir(root_dir)):
            folders.append(root_dir)
    except Exception:
        pass

    # 하위 1단계 폴더 검사
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        if not os.path.isdir(item_path):
            continue
        try:
            if any(fn.lower().endswith('_aux.xml') for fn in os.listdir(item_path)):
                folders.append(item_path)
        except Exception:
            continue

    # 중복 제거 및 정렬
    folders = sorted(list(set(folders)))
    return folders


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python batch_process_all.py <루트폴더경로>")
        print('예시: python batch_process_all.py "D:\\국토정보위성"')
        sys.exit(1)
    
    root_dir = sys.argv[1]
    
    if not os.path.isdir(root_dir):
        print(f"오류: '{root_dir}' 폴더를 찾을 수 없습니다.")
        sys.exit(1)
    
    # 처리 대상 폴더 찾기
    folders = find_kompsat_folders(root_dir)
    
    if not folders:
        print(f"'{root_dir}'에서 *_Aux.xml 이 포함된 폴더를 찾을 수 없습니다.")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print(" 국토정보위성 배치 처리")
    print("=" * 70)
    print(f"발견된 처리 대상 폴더: {len(folders)}개")
    for i, folder in enumerate(folders, 1):
        print(f"  {i}. {os.path.basename(folder)}")
    
    print("\n" + "=" * 70)
    
    # 처리 결과 추적
    results = {
        'success': [],
        'failed': []
    }
    
    start_time = datetime.now()
    
    # 각 폴더 처리
    for i, folder in enumerate(folders, 1):
        print(f"\n[{i}/{len(folders)}] 처리 중: {os.path.basename(folder)}")
        print("-" * 70)
        
        processor = KompsatProcessor(folder)
        
        try:
            if processor.process():
                results['success'].append(folder)
            else:
                results['failed'].append(folder)
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            results['failed'].append(folder)
    
    end_time = datetime.now()
    elapsed = end_time - start_time
    
    # 최종 보고서
    print("\n" + "=" * 70)
    print(" 배치 처리 완료 보고서")
    print("=" * 70)
    print(f"처리 시간: {elapsed}")
    print(f"전체 폴더: {len(folders)}개")
    print(f"성공: {len(results['success'])}개")
    print(f"실패: {len(results['failed'])}개")
    
    if results['success']:
        print("\n✓ 성공한 폴더:")
        for folder in results['success']:
            print(f"  • {os.path.basename(folder)}")
    
    if results['failed']:
        print("\n✗ 실패한 폴더:")
        for folder in results['failed']:
            print(f"  • {os.path.basename(folder)}")
    
    print("\n" + "=" * 70)
    
    sys.exit(0 if not results['failed'] else 1)


if __name__ == '__main__':
    main()
