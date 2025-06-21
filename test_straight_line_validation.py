#!/usr/bin/env python3
"""
直線判定ロジックの動作確認テスト

人工的に179度の角度を作成して、直線判定が正しく動作することを検証
"""

import math
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from effects.round_corners_effect import RoundCornersEffect

def test_straight_line_logic():
    """直線判定ロジックの単体テスト"""
    print("=== 直線判定ロジック単体テスト ===")
    
    # RoundCornersEffectのインスタンスを作成
    effect = RoundCornersEffect()
    effect.params = {'radius': 10, 'angle_threshold': 100}
    
    # テスト用の輪郭データを作成（179度の角度を含む）
    # 3つの点で179度の角度を作成
    test_contour = {
        'coords': [
            (0, 0),      # P1
            (100, 0),    # P2 (中心点)
            (200, 1)     # P3 (ほぼ直線、179度の角度)
        ],
        'flags': [1, 1, 1]  # 全てオンカーブ点
    }
    
    print("テスト用輪郭データ:")
    print(f"  P1: {test_contour['coords'][0]}")
    print(f"  P2: {test_contour['coords'][1]} (中心点)")
    print(f"  P3: {test_contour['coords'][2]}")
    
    # 角度を手動計算して確認
    p1, p2, p3 = test_contour['coords']
    v1 = (p2[0] - p1[0], p2[1] - p1[1])  # (100, 0)
    v2 = (p3[0] - p2[0], p3[1] - p2[1])  # (100, 1)
    
    norm1 = math.hypot(*v1)  # 100
    norm2 = math.hypot(*v2)  # ~100.005
    
    dot = v1[0]*v2[0] + v1[1]*v2[1]  # 100*100 + 0*1 = 10000
    angle = math.acos(max(-1, min(1, dot / (norm1 * norm2))))
    angle_degrees = math.degrees(angle)
    
    print(f"\n手動計算による角度: {angle_degrees:.1f}度")
    print("この角度は178度～182度の範囲内なので、直線として判定されるはず")
    
    print("\n角丸処理を実行...")
    result = effect._round_corners_direct(test_contour, 10, 100)
    
    print(f"\n結果:")
    print(f"  元の座標数: {len(test_contour['coords'])}")
    print(f"  処理後座標数: {len(result['coords'])}")
    
    if len(result['coords']) == len(test_contour['coords']):
        print("✅ 成功: 直線判定により角丸処理がスキップされました")
    else:
        print("❌ 失敗: 直線が角丸処理されてしまいました")
    
    return len(result['coords']) == len(test_contour['coords'])

def test_normal_corner():
    """通常の角（90度）が正しく処理されることを確認"""
    print("\n=== 通常の角処理テスト ===")
    
    effect = RoundCornersEffect()
    effect.params = {'radius': 10, 'angle_threshold': 100}
    
    # 90度の角を作成
    test_contour = {
        'coords': [
            (0, 0),      # P1
            (100, 0),    # P2 (中心点)
            (100, 100)   # P3 (90度の角)
        ],
        'flags': [1, 1, 1]
    }
    
    print("テスト用輪郭データ (90度の角):")
    print(f"  P1: {test_contour['coords'][0]}")
    print(f"  P2: {test_contour['coords'][1]} (中心点)")
    print(f"  P3: {test_contour['coords'][2]}")
    
    print("\n角丸処理を実行...")
    result = effect._round_corners_direct(test_contour, 10, 100)
    
    print(f"\n結果:")
    print(f"  元の座標数: {len(test_contour['coords'])}")
    print(f"  処理後座標数: {len(result['coords'])}")
    
    if len(result['coords']) > len(test_contour['coords']):
        print("✅ 成功: 90度の角が正しく角丸処理されました")
        return True
    else:
        print("❌ 失敗: 90度の角が処理されませんでした")
        return False

if __name__ == "__main__":
    print("直線判定修正の検証テストを開始します\n")
    
    # テスト1: 直線判定
    straight_test_passed = test_straight_line_logic()
    
    # テスト2: 通常の角処理
    corner_test_passed = test_normal_corner()
    
    print(f"\n=== 最終結果 ===")
    print(f"直線判定テスト: {'✅ 成功' if straight_test_passed else '❌ 失敗'}")
    print(f"通常角処理テスト: {'✅ 成功' if corner_test_passed else '❌ 失敗'}")
    
    if straight_test_passed and corner_test_passed:
        print("\n🎉 全てのテストが成功しました！")
        print("修正により、直線部分が誤って処理される問題が解決されました。")
    else:
        print("\n⚠️  一部のテストが失敗しました。")