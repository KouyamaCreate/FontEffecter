#!/usr/bin/env python3
"""
直線判定修正のテストスクリプト

修正内容:
- 178度～182度の角度を直線として認識し、角丸処理から除外
- 二段階判定の実装確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from font_processor import FontProcessor

def test_straight_line_detection():
    """直線判定修正のテスト"""
    print("=== 直線判定修正テスト開始 ===")
    
    # 設定を作成（テスト用に小さなradius値を使用）
    test_config = {
        "input_font": "/Users/koseiyamamoto/Library/CloudStorage/Dropbox/Downloads/Inter,Manrope,Noto_Sans,Noto_Sans_JP (1)/Noto_Sans_JP/static/NotoSansJP-Medium.ttf",
        "output_font": "test_output_straight_line_fix.otf",
        "effects": [
            {
                "name": "round_corners",
                "params": {
                    "radius": 20,  # 小さめの値でテスト
                    "angle_threshold": 100  # 現在の設定値を使用
                }
            }
        ]
    }
    
    try:
        # フォントプロセッサーを初期化
        processor = FontProcessor.from_config_dict(test_config)
        
        print("フォントを読み込み中...")
        font = processor.load_font()
        
        print("角丸エフェクトを適用中...")
        print("--- 直線判定ログを確認してください ---")
        modified_font = processor.apply_effects(font)
        
        print("修正されたフォントを保存中...")
        processor.save_font(modified_font)
        
        print(f"テスト完了: {test_config['output_font']} に保存されました")
        print("\n=== 期待される結果 ===")
        print("- 178度～182度の角度: '直線判定: 角度XXX.X度 - 直線として除外' のログが表示される")
        print("- 100度未満の角度: '角検出: 角度XXX.X度 - 角丸処理対象' のログが表示される")
        print("- 直線部分が角丸処理されず、本来の角のみが処理される")
        
    except FileNotFoundError as e:
        print(f"エラー: フォントファイルが見つかりません - {e}")
        print("フォントファイルのパスを確認してください")
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_straight_line_detection()