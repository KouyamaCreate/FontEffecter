#!/usr/bin/env python3
"""
最終修正の検証テスト
pathops統合処理を無効化した後の動作確認
"""

import sys
from fontTools.ttLib import TTFont
from effects.round_corners_effect import RoundCornersEffect

def test_final_fix():
    """最終修正の検証"""
    
    print("=== 最終修正検証テスト開始 ===")
    
    # システムフォントを使用
    font_path = "/System/Library/Fonts/Geneva.ttf"
    
    try:
        # フォントを読み込み
        font = TTFont(font_path)
        print(f"テスト用フォント: {font_path}")
        
        # 角丸エフェクトを適用
        effect = RoundCornersEffect()
        effect.params = {'radius': 10}  # 適度な半径でテスト
        
        print("角丸処理を実行中...")
        result_font = effect.apply(font)
        
        # 結果をファイルに保存
        output_path = "test_final_fix_output.otf"
        result_font.save(output_path)
        print(f"処理結果を保存: {output_path}")
        
        # 保存したフォントを再読み込みして検証
        print("保存したフォントの検証中...")
        verification_font = TTFont(output_path)
        
        glyf_table = verification_font['glyf']
        test_glyphs = ['A', 'B', 'O']
        
        for glyph_name in test_glyphs:
            if glyph_name in glyf_table:
                glyph = glyf_table[glyph_name]
                if not glyph.isComposite() and hasattr(glyph, 'coordinates') and glyph.coordinates:
                    print(f"グリフ '{glyph_name}': 座標数={len(glyph.coordinates)}, 輪郭数={len(glyph.endPtsOfContours)}")
        
        print("=== 検証完了: フォントファイルが正常に作成されました ===")
        return True
        
    except Exception as e:
        print(f"ERROR: 検証中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_final_fix()
    sys.exit(0 if success else 1)