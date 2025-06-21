#!/usr/bin/env python3
"""
詳細デバッグ: 3点輪郭での各点の角度計算を詳しく調査
"""

import math
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def calculate_angle(p1, p2, p3):
    """3点間の角度を計算"""
    v1 = (p2[0] - p1[0], p2[1] - p1[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    norm1 = math.hypot(*v1)
    norm2 = math.hypot(*v2)
    
    if norm1 == 0 or norm2 == 0:
        return None
    
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    angle = math.acos(max(-1, min(1, dot / (norm1 * norm2))))
    return math.degrees(angle)

def analyze_contour():
    """3点輪郭の詳細分析"""
    print("=== 3点輪郭の詳細分析 ===")
    
    # テスト用の輪郭データ（179度の角度を含む）
    coords = [
        (0, 0),      # P0
        (100, 0),    # P1 (中心点)
        (200, 1)     # P2 (ほぼ直線、179度の角度)
    ]
    
    print("座標:")
    for i, coord in enumerate(coords):
        print(f"  P{i}: {coord}")
    
    print("\n各点を中心とした角度計算:")
    
    # 各点を中心として角度を計算（輪郭処理と同じロジック）
    for i in range(len(coords)):
        p1 = coords[(i - 1) % len(coords)]  # 前の点
        p2 = coords[i]                      # 中心点
        p3 = coords[(i + 1) % len(coords)]  # 次の点
        
        angle = calculate_angle(p1, p2, p3)
        
        print(f"\n  点P{i}を中心とした角度:")
        print(f"    前の点: P{(i-1)%len(coords)} {p1}")
        print(f"    中心点: P{i} {p2}")
        print(f"    次の点: P{(i+1)%len(coords)} {p3}")
        print(f"    角度: {angle:.1f}度")
        
        # 直線判定
        if angle is not None:
            straight_line_tolerance = 2.0
            if abs(angle - 180.0) <= straight_line_tolerance:
                print(f"    → 直線判定: 除外される")
            elif angle < 100:  # angle_threshold = 100
                print(f"    → 角丸処理: 対象となる")
            else:
                print(f"    → 角度閾値: 除外される")

if __name__ == "__main__":
    analyze_contour()