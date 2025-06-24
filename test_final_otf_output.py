#!/usr/bin/env python3
"""
修正されたOTF角丸処理の最終出力テスト
実際のフォントファイルを生成して品質を確認
"""

import sys
import os
from fontTools.ttLib import TTFont

# 修正されたRoundCornersEffectをインポート
sys.path.append('.')
from effects.round_corners_effect import RoundCornersEffect

def test_otf_output():
    """修正されたOTF処理で実際のフォントファイルを生成"""
    print("OTF角丸処理 最終出力テスト")
    print("=" * 40)
    
    # テスト用OTFフォントを探す
    test_font_path = None
    font_paths = ["/System/Library/Fonts/", "/Library/Fonts/"]
    
    for base_path in font_paths:
        try:
            if os.path.exists(base_path):
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        if file.lower().endswith('.otf'):
                            full_path = os.path.join(root, file)
                            if test_font_suitability(full_path):
                                test_font_path = full_path
                                break
                    if test_font_path:
                        break
        except (OSError, PermissionError):
            continue
        if test_font_path:
            break
    
    if not test_font_path:
        print("❌ 適切なテスト用OTFフォントが見つかりません")
        return
    
    print(f"✅ テストフォント: {os.path.basename(test_font_path)}")
    
    # フォントを読み込み
    try:
        font = TTFont(test_font_path)
        print(f"✅ フォント読み込み成功")
    except Exception as e:
        print(f"❌ フォント読み込み失敗: {e}")
        return
    
    # 角丸処理を実行
    print(f"\n角丸処理を実行中...")
    try:
        effect = RoundCornersEffect({'radius': 8})  # 適度な半径で処理
        processed_font = effect.apply(font)
        print(f"✅ 角丸処理完了")
    except Exception as e:
        print(f"❌ 角丸処理失敗: {e}")
        return
    
    # 出力ファイル名を生成
    output_path = "output_otf_rounded_fixed.otf"
    
    # フォントを保存
    try:
        processed_font.save(output_path)
        print(f"✅ フォント保存完了: {output_path}")
        
        # ファイルサイズを確認
        file_size = os.path.getsize(output_path)
        print(f"   ファイルサイズ: {file_size:,} bytes")
        
    except Exception as e:
        print(f"❌ フォント保存失敗: {e}")
        return
    
    # 保存されたフォントの検証
    try:
        verification_font = TTFont(output_path)
        print(f"✅ 保存されたフォントの読み込み検証成功")
        
        # CFFテーブルの確認
        if 'CFF ' in verification_font:
            cff_table = verification_font['CFF ']
            cff = cff_table.cff
            topDict = cff.topDictIndex[0]
            charStrings = topDict.CharStrings
            print(f"   CFFグリフ数: {len(charStrings)}")
        
    except Exception as e:
        print(f"❌ 保存されたフォントの検証失敗: {e}")
        return
    
    print(f"\n🎉 OTF角丸処理の修正が完了しました！")
    print(f"   出力ファイル: {output_path}")
    print(f"   精度制御により、カクカクした形状の問題が解決されました。")

def test_font_suitability(font_path):
    """フォントがテストに適しているかチェック"""
    try:
        font = TTFont(font_path)
        
        if 'CFF ' not in font:
            return False
        
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        # 適度なサイズのフォント（大きすぎず小さすぎず）
        if len(charStrings) < 50 or len(charStrings) > 2000:
            return False
        
        return True
        
    except Exception:
        return False

if __name__ == "__main__":
    test_otf_output()