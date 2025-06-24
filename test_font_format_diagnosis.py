#!/usr/bin/env python3
"""
フォント形式診断テスト
KeyError: 'glyf' エラーの原因を特定するためのテスト
"""

import sys
import os
from fontTools.ttLib import TTFont

def diagnose_font_format(font_path):
    """フォント形式を診断する"""
    print(f"=== フォント形式診断: {font_path} ===")
    
    if not os.path.exists(font_path):
        print(f"ERROR: ファイルが見つかりません: {font_path}")
        return False
    
    try:
        font = TTFont(font_path)
        
        print(f"ファイル拡張子: {os.path.splitext(font_path)[1]}")
        print(f"利用可能なテーブル: {sorted(font.keys())}")
        
        # フォント形式の判定
        has_glyf = 'glyf' in font
        has_cff = 'CFF ' in font
        has_cff2 = 'CFF2' in font
        
        print(f"TrueType (glyf テーブル): {'あり' if has_glyf else 'なし'}")
        print(f"OpenType/CFF (CFF  テーブル): {'あり' if has_cff else 'なし'}")
        print(f"OpenType/CFF2 (CFF2 テーブル): {'あり' if has_cff2 else 'なし'}")
        
        # フォント形式の判定結果
        if has_glyf:
            print("判定結果: TrueTypeフォント (.ttf)")
            print("現在の実装: 対応済み")
        elif has_cff:
            print("判定結果: OpenType/CFFフォント (.otf)")
            print("現在の実装: 未対応 - KeyError: 'glyf' エラーの原因")
        elif has_cff2:
            print("判定結果: OpenType/CFF2フォント")
            print("現在の実装: 未対応")
        else:
            print("判定結果: 不明なフォント形式")
            print("現在の実装: 未対応")
        
        # グリフ数の確認
        if has_glyf:
            glyf_table = font['glyf']
            print(f"グリフ数: {len(glyf_table)} 個")
        elif has_cff:
            cff_table = font['CFF ']
            print(f"CFF テーブル情報: {type(cff_table)}")
            # CFFテーブルからグリフ数を取得する方法を調査
            try:
                cff = cff_table.cff
                topDict = cff.topDictIndex[0]
                charStrings = topDict.CharStrings
                print(f"グリフ数: {len(charStrings)} 個")
            except Exception as e:
                print(f"CFFグリフ数取得エラー: {e}")
        
        font.close()
        return True
        
    except Exception as e:
        print(f"ERROR: フォント読み込みエラー: {e}")
        return False

def main():
    """メイン関数"""
    print("フォント形式診断テストを開始します...")
    
    # テスト対象のフォントファイルを探す
    test_fonts = []
    
    # 現在のディレクトリでフォントファイルを探す
    for file in os.listdir('.'):
        if file.endswith(('.ttf', '.otf')):
            test_fonts.append(file)
    
    if not test_fonts:
        print("テスト用のフォントファイル (.ttf または .otf) が見つかりません。")
        print("フォントファイルを現在のディレクトリに配置してください。")
        return
    
    print(f"見つかったフォントファイル: {test_fonts}")
    print()
    
    for font_path in test_fonts:
        diagnose_font_format(font_path)
        print()
    
    print("診断完了")

if __name__ == "__main__":
    main()