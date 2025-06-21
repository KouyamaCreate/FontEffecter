#!/usr/bin/env python3
"""
直線判定問題のデバッグスクリプト
角丸処理が一切行われない問題を調査する
"""

import sys
import os
from fontTools.ttLib import TTFont

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from effects.round_corners_effect import RoundCornersEffect

def debug_straight_line_detection():
    """直線判定アルゴリズムの問題を調査"""
    
    print("=== 直線判定問題デバッグ開始 ===")
    
    # テスト用フォントファイルを探す
    test_fonts = [
        "test_output_straight_line_fix.otf",
        "output_rounded.otf"
    ]
    
    font_path = None
    for font_file in test_fonts:
        if os.path.exists(font_file):
            font_path = font_file
            break
    
    if not font_path:
        print("エラー: テスト用フォントファイルが見つかりません")
        return
    
    print(f"使用するフォント: {font_path}")
    
    try:
        # フォントを読み込み
        font = TTFont(font_path)
        
        # 角丸エフェクトを作成（デバッグモード）
        effect = RoundCornersEffect()
        effect.params = {
            'radius': 10,  # 十分な半径を設定
            'angle_threshold': 160
        }
        
        print(f"設定 - 半径: {effect.params['radius']}, 角度閾値: {effect.params['angle_threshold']}")
        
        # 少数のグリフのみをテスト（詳細な出力のため）
        glyf_table = font['glyf']
        test_glyphs = []
        
        # 最初の5つの有効なグリフを選択
        for glyph_name in list(glyf_table.keys())[:10]:
            glyph = glyf_table[glyph_name]
            if (not glyph.isComposite() and 
                hasattr(glyph, "coordinates") and 
                glyph.numberOfContours > 0 and
                glyph.coordinates):
                test_glyphs.append(glyph_name)
                if len(test_glyphs) >= 3:  # 3つのグリフをテスト
                    break
        
        print(f"テスト対象グリフ: {test_glyphs}")
        
        # 各グリフで直線判定をテスト
        for glyph_name in test_glyphs:
            print(f"\n--- グリフ '{glyph_name}' のデバッグ ---")
            
            glyph = glyf_table[glyph_name]
            
            # 座標データを取得
            original_coords = list(glyph.coordinates)
            original_endPts = list(glyph.endPtsOfContours)
            original_flags = list(glyph.flags)
            
            print(f"座標数: {len(original_coords)}, 輪郭数: {len(original_endPts)}")
            
            # 輪郭を抽出
            contours = effect._extract_contours_from_coordinates(
                original_coords, original_endPts, original_flags
            )
            
            # 各輪郭で直線判定をテスト
            for contour_idx, contour in enumerate(contours):
                print(f"\n  輪郭 {contour_idx + 1}:")
                print(f"  点数: {len(contour['coords'])}")
                
                if len(contour['coords']) >= 3:
                    # 角丸処理を実行（デバッグ出力付き）
                    rounded_contour = effect._round_corners_direct(
                        contour, effect.params['radius'], effect.params['angle_threshold']
                    )
                    
                    print(f"  処理後の点数: {len(rounded_contour['coords'])}")
        
        print("\n=== デバッグ完了 ===")
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_straight_line_detection()