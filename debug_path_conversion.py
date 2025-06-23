#!/usr/bin/env python3
"""
パス変換処理の徹底デバッグスクリプト
単純なグリフ（四角形）を対象にデータ変換の各段階を検証
"""

import sys
from fontTools.ttLib import TTFont
from effects.round_corners_effect import RoundCornersEffect

def debug_path_conversion():
    """パス変換処理をデバッグ"""
    
    print("=== パス変換処理デバッグ開始 ===")
    
    # テスト用フォントファイルを探す（システムフォントを使用）
    test_fonts = [
        "/System/Library/Fonts/Geneva.ttf",
        "/System/Library/Fonts/Symbol.ttf",
        "/System/Library/Fonts/SFNSMono.ttf"
    ]
    
    font_path = None
    for font_file in test_fonts:
        try:
            font = TTFont(font_file)
            font_path = font_file
            print(f"テスト用フォント: {font_file}")
            break
        except Exception as e:
            print(f"フォント {font_file} の読み込みに失敗: {e}")
            continue
    
    if not font_path:
        print("ERROR: テスト用フォントファイルが見つかりません")
        return
    
    # フォントを読み込み
    font = TTFont(font_path)
    
    # 単純なグリフを探す（四角形や基本的な文字）
    glyf_table = font['glyf']
    target_glyphs = []
    
    # 基本的な文字を優先的に選択
    priority_chars = ['A', 'B', 'O', 'D', 'P', 'R', 'a', 'b', 'o', 'd', 'p', 'q']
    
    for char in priority_chars:
        if char in glyf_table:
            glyph = glyf_table[char]
            if not glyph.isComposite() and hasattr(glyph, 'coordinates') and glyph.coordinates:
                target_glyphs.append(char)
                if len(target_glyphs) >= 3:  # 最大3文字をテスト
                    break
    
    # 優先文字が見つからない場合は他の文字を探す
    if not target_glyphs:
        for glyph_name in list(glyf_table.keys())[:10]:
            glyph = glyf_table[glyph_name]
            if not glyph.isComposite() and hasattr(glyph, 'coordinates') and glyph.coordinates:
                target_glyphs.append(glyph_name)
                if len(target_glyphs) >= 3:
                    break
    
    if not target_glyphs:
        print("ERROR: テスト対象のグリフが見つかりません")
        return
    
    print(f"テスト対象グリフ: {target_glyphs}")
    
    # 角丸エフェクトを適用（デバッグログ付き）
    effect = RoundCornersEffect()
    effect.params = {'radius': 5}  # 小さな半径でテスト
    
    print("\n=== 角丸処理実行（デバッグログ付き） ===")
    
    try:
        # 直接エフェクトを適用
        result_font = effect.apply(font)
        print("\n=== デバッグ完了 ===")
    except Exception as e:
        print(f"ERROR: デバッグ中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_path_conversion()