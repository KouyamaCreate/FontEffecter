#!/usr/bin/env python3
"""
OpenType/CFFフォント対応修正のテスト
KeyError: 'glyf' エラーの修正を検証
"""

import sys
import os
from fontTools.ttLib import TTFont
from effects.round_corners_effect import RoundCornersEffect

def test_cff_font_processing():
    """OpenType/CFFフォントの処理をテスト"""
    print("=== OpenType/CFFフォント対応テスト ===")
    
    # OpenType/CFFフォントを探す
    cff_fonts = []
    for file in os.listdir('.'):
        if file.endswith('.otf'):
            try:
                font = TTFont(file)
                if 'CFF ' in font:
                    cff_fonts.append(file)
                font.close()
            except:
                pass
    
    if not cff_fonts:
        print("OpenType/CFFフォントが見つかりません。")
        return False
    
    print(f"テスト対象のCFFフォント: {cff_fonts}")
    
    for font_path in cff_fonts:
        print(f"\n--- {font_path} のテスト ---")
        
        try:
            # フォントを読み込み
            font = TTFont(font_path)
            
            # 角丸エフェクトを作成
            params = {'radius': 5, 'angle_threshold': 160}
            effect = RoundCornersEffect(params)
            
            print("角丸処理を実行中...")
            
            # 角丸処理を適用
            processed_font = effect.apply(font, radius=5)
            
            # 出力ファイル名を生成
            base_name = os.path.splitext(font_path)[0]
            output_path = f"{base_name}_cff_test_output.otf"
            
            # 処理済みフォントを保存
            processed_font.save(output_path)
            
            print(f"成功: {output_path} に保存されました")
            
            font.close()
            
        except Exception as e:
            print(f"エラー: {font_path} の処理中に例外が発生: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

def test_truetype_font_processing():
    """TrueTypeフォントの処理もテスト（回帰テスト）"""
    print("\n=== TrueTypeフォント回帰テスト ===")
    
    # TrueTypeフォントを探す
    ttf_fonts = []
    for file in os.listdir('.'):
        if file.endswith(('.ttf', '.otf')):
            try:
                font = TTFont(file)
                if 'glyf' in font:
                    ttf_fonts.append(file)
                font.close()
            except:
                pass
    
    if not ttf_fonts:
        print("TrueTypeフォントが見つかりません。")
        return True  # CFFテストが成功していれば問題なし
    
    print(f"テスト対象のTrueTypeフォント: {ttf_fonts[:2]}")  # 最初の2つだけテスト
    
    for font_path in ttf_fonts[:2]:
        print(f"\n--- {font_path} のテスト ---")
        
        try:
            # フォントを読み込み
            font = TTFont(font_path)
            
            # 角丸エフェクトを作成
            params = {'radius': 3, 'angle_threshold': 160}
            effect = RoundCornersEffect(params)
            
            print("角丸処理を実行中...")
            
            # 角丸処理を適用
            processed_font = effect.apply(font, radius=3)
            
            print("成功: TrueTypeフォントの処理も正常に動作しています")
            
            font.close()
            
        except Exception as e:
            print(f"エラー: {font_path} の処理中に例外が発生: {str(e)}")
            return False
    
    return True

def main():
    """メイン関数"""
    print("OpenType/CFFフォント対応修正のテストを開始します...")
    
    # CFFフォントのテスト
    cff_success = test_cff_font_processing()
    
    # TrueTypeフォントの回帰テスト
    ttf_success = test_truetype_font_processing()
    
    print("\n=== テスト結果 ===")
    print(f"OpenType/CFFフォント対応: {'成功' if cff_success else '失敗'}")
    print(f"TrueTypeフォント回帰テスト: {'成功' if ttf_success else '失敗'}")
    
    if cff_success and ttf_success:
        print("✅ すべてのテストが成功しました！")
        print("KeyError: 'glyf' エラーの修正が完了しました。")
    else:
        print("❌ テストに失敗しました。")
    
    return cff_success and ttf_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)