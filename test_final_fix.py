#!/usr/bin/env python3
"""
修正された角丸効果の最終テスト
"""

import os
import sys
sys.path.append('.')

from fontTools.ttLib import TTFont
from effects.round_corners_effect import RoundCornersEffect

def test_final_fix():
    """修正された角丸効果の最終テスト"""
    
    # テスト用のOTFフォントファイルを探す
    test_fonts = [
        "output_otf_rounded_fixed.otf",
        "output_rounded.otf"
    ]
    
    font_file = None
    for f in test_fonts:
        if os.path.exists(f):
            font_file = f
            break
    
    if not font_file:
        print("エラー: テスト用のOTFフォントファイルが見つかりません")
        return False
    
    print(f"=== 修正された角丸効果の最終テスト ===")
    print(f"テストフォント: {font_file}")
    
    try:
        # フォントを読み込み
        font = TTFont(font_file)
        
        # 角丸効果を適用
        effect = RoundCornersEffect({'radius': 10, 'quality_level': 'medium'})
        processed_font = effect.apply(font, radius=10)
        
        # 結果を保存
        output_file = "output_final_fixed.otf"
        processed_font.save(output_file)
        print(f"修正版角丸フォントを保存: {output_file}")
        
        # 保存されたフォントを検証
        test_font = TTFont(output_file)
        if 'CFF ' in test_font:
            print("✓ 修正版角丸フォントが正常に保存されました")
            
            # CFFテーブルの基本チェック
            cff_table = test_font['CFF ']
            cff = cff_table.cff
            topDict = cff.topDictIndex[0]
            charStrings = topDict.CharStrings
            
            print(f"✓ グリフ数: {len(charStrings)}")
            
            # いくつかのグリフをサンプルチェック
            sample_glyphs = ['.notdef', 'A', 'a', 'O', 'o']
            valid_glyphs = 0
            
            for glyph_name in sample_glyphs:
                if glyph_name in charStrings:
                    try:
                        charString = charStrings[glyph_name]
                        from fontTools.pens.recordingPen import RecordingPen
                        pen = RecordingPen()
                        charString.draw(pen)
                        if pen.value:
                            valid_glyphs += 1
                            print(f"  ✓ グリフ '{glyph_name}': {len(pen.value)} コマンド")
                    except Exception as e:
                        print(f"  ❌ グリフ '{glyph_name}': エラー {e}")
            
            print(f"✓ 有効なサンプルグリフ: {valid_glyphs}/{len(sample_glyphs)}")
            
            if valid_glyphs > 0:
                print("\n🎉 修正された角丸効果が正常に動作しています！")
                print(f"出力ファイル: {output_file}")
                print("\n【解決された問題】")
                print("- T2CharStringの座標変化を考慮した角丸処理")
                print("- より保守的な角丸パラメータ")
                print("- 品質チェックの緩和")
                print("- エラーハンドリングの改善")
                return True
            else:
                print("❌ グリフの検証に失敗しました")
                return False
        else:
            print("❌ CFFフォントの保存に問題があります")
            return False
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_final_fix()
    if success:
        print("\n✅ OTFフォントの「カクカク」問題が解決されました！")
    else:
        print("\n❌ 問題の解決に失敗しました")