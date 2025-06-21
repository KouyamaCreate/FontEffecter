#!/usr/bin/env python3
"""
角度分布の詳細診断スクリプト

170度以上の角度の分布を確認し、直線判定が正しく動作するかテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from font_processor import FontProcessor

def test_angle_distribution():
    """角度分布の詳細診断"""
    print("=== 角度分布詳細診断テスト ===")
    
    # より小さなradius値でテスト（より多くの角度を検出）
    test_config = {
        "input_font": "/Users/koseiyamamoto/Library/CloudStorage/Dropbox/Downloads/Inter,Manrope,Noto_Sans,Noto_Sans_JP (1)/Noto_Sans_JP/static/NotoSansJP-Medium.ttf",
        "output_font": "test_angle_distribution.otf",
        "effects": [
            {
                "name": "round_corners",
                "params": {
                    "radius": 5,  # 非常に小さな値
                    "angle_threshold": 179  # 非常に高い閾値（ほぼ全ての角度を処理対象にする）
                }
            }
        ]
    }
    
    try:
        processor = FontProcessor.from_config_dict(test_config)
        print("フォントを読み込み中...")
        font = processor.load_font()
        
        print("角丸エフェクトを適用中（最初の5グリフのみ処理）...")
        print("--- 170度以上の角度分布を確認 ---")
        
        # 最初の数グリフのみ処理するように一時的に制限
        glyf_table = font['glyf']
        glyph_names = list(glyf_table.keys())[:5]  # 最初の5グリフのみ
        
        modified_font = processor.apply_effects(font)
        
        print("テスト完了")
        print("\n=== 診断結果の期待値 ===")
        print("- 170度～177度: '大角度検出: 角度XXX.X度 - 直線に近いが処理対象'")
        print("- 178度～182度: '直線判定: 角度XXX.X度 - 直線として除外'")
        print("- 179度に近い角度が存在する場合、直線判定が動作することを確認")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_angle_distribution()