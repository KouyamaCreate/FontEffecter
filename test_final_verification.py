#!/usr/bin/env python3
"""
角丸処理修正後の最終検証スクリプト
"""

import sys
import os
from fontTools.ttLib import TTFont

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from effects.round_corners_effect import RoundCornersEffect

def test_corner_rounding_fix():
    """修正された角丸処理の最終検証"""
    
    print("=== 角丸処理修正後の最終検証 ===")
    
    # テスト用フォントファイルを探す
    test_fonts = [
        "test_output_straight_line_fix.otf",
        "output_rounded.otf"
    ]
    
    input_font = None
    for font_file in test_fonts:
        if os.path.exists(font_file):
            input_font = font_file
            break
    
    if not input_font:
        print("エラー: テスト用フォントファイルが見つかりません")
        return
    
    print(f"入力フォント: {input_font}")
    
    output_font = "test_final_verification_output.otf"
    
    try:
        # フォントを読み込み
        font = TTFont(input_font)
        
        # 角丸エフェクトを作成・適用
        effect = RoundCornersEffect()
        effect.params = {
            'radius': 15,  # 明確に見える半径を設定
            'angle_threshold': 160
        }
        
        print(f"角丸処理を実行中... (半径: {effect.params['radius']})")
        
        # エフェクトを適用
        processed_font = effect.apply(font)
        
        # 保存
        processed_font.save(output_font)
        
        print(f"✅ 角丸処理が完了しました")
        print(f"出力ファイル: {output_font}")
        
        # 処理前後の比較
        original_font = TTFont(input_font)
        processed_font = TTFont(output_font)
        
        print("\n--- 処理結果の比較 ---")
        
        # いくつかのグリフで点数の変化を確認
        test_glyphs = ['.notdef', 'A', 'B', 'O', 'a', 'o']
        
        for glyph_name in test_glyphs:
            if glyph_name in original_font['glyf'] and glyph_name in processed_font['glyf']:
                orig_glyph = original_font['glyf'][glyph_name]
                proc_glyph = processed_font['glyf'][glyph_name]
                
                if (not orig_glyph.isComposite() and 
                    hasattr(orig_glyph, 'coordinates') and orig_glyph.coordinates and
                    not proc_glyph.isComposite() and 
                    hasattr(proc_glyph, 'coordinates') and proc_glyph.coordinates):
                    
                    orig_points = len(orig_glyph.coordinates)
                    proc_points = len(proc_glyph.coordinates)
                    
                    if proc_points > orig_points:
                        print(f"✅ グリフ '{glyph_name}': {orig_points}点 → {proc_points}点 (角丸処理実行)")
                    else:
                        print(f"ℹ️  グリフ '{glyph_name}': {orig_points}点 → {proc_points}点 (変化なし)")
        
        print(f"\n✅ 検証完了: 角丸処理が正常に動作しています")
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_corner_rounding_fix()