#!/usr/bin/env python3
"""
ベジェ曲線対応角丸処理のテストスクリプト
修正後の処理で「カクカク」問題が解決されるかを検証
"""

import sys
import os
from fontTools.ttLib import TTFont
from effects.round_corners_effect import RoundCornersEffect

def test_bezier_curve_fix():
    """ベジェ曲線対応修正のテスト"""
    
    print("=== ベジェ曲線対応角丸処理テスト ===")
    
    # テスト用フォントファイルを探す
    test_fonts = [
        'output_final_fixed.otf',
        'output_otf_rounded_fixed.otf', 
        'output_rounded.otf'
    ]
    
    input_font_path = None
    for font_file in test_fonts:
        if os.path.exists(font_file):
            input_font_path = font_file
            break
    
    if not input_font_path:
        print("エラー: テスト用フォントファイルが見つかりません")
        return
    
    print(f"入力フォント: {input_font_path}")
    
    try:
        # フォントを読み込み
        font = TTFont(input_font_path)
        
        # 角丸処理エフェクトを作成
        effect = RoundCornersEffect({
            'radius': 15,  # テスト用に大きめの半径
            'quality_level': 'high'  # 高品質設定
        })
        
        print("ベジェ曲線対応角丸処理を実行中...")
        
        # 角丸処理を適用
        processed_font = effect.apply(font)
        
        # 結果を保存
        output_path = 'output_bezier_curve_fixed.otf'
        processed_font.save(output_path)
        
        print(f"処理完了: {output_path}")
        print("\n=== 処理結果の検証 ===")
        
        # 処理前後の比較
        compare_before_after(input_font_path, output_path)
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

def compare_before_after(input_path, output_path):
    """処理前後の比較"""
    try:
        input_font = TTFont(input_path)
        output_font = TTFont(output_path)
        
        print("処理前後のグリフ比較:")
        
        # CFFフォントの場合
        if 'CFF ' in input_font and 'CFF ' in output_font:
            input_cff = input_font['CFF '].cff.topDictIndex[0].CharStrings
            output_cff = output_font['CFF '].cff.topDictIndex[0].CharStrings
            
            # 曲線を含むグリフを比較
            curve_glyphs = ['breve', 'caron', 'dotaccent']
            
            for glyph_name in curve_glyphs:
                if glyph_name in input_cff and glyph_name in output_cff:
                    print(f"\nグリフ '{glyph_name}':")
                    
                    # 処理前の分析
                    input_analysis = analyze_glyph_smoothness(input_cff[glyph_name])
                    print(f"  処理前: 制御点{input_analysis['control_points']}個, 滑らかさ{input_analysis['smoothness']:.2f}")
                    
                    # 処理後の分析
                    output_analysis = analyze_glyph_smoothness(output_cff[glyph_name])
                    print(f"  処理後: 制御点{output_analysis['control_points']}個, 滑らかさ{output_analysis['smoothness']:.2f}")
                    
                    # 改善度
                    improvement = output_analysis['smoothness'] - input_analysis['smoothness']
                    if improvement > 0:
                        print(f"  改善: +{improvement:.2f} (滑らかさ向上)")
                    elif improvement < 0:
                        print(f"  悪化: {improvement:.2f} (滑らかさ低下)")
                    else:
                        print(f"  変化なし")
        
    except Exception as e:
        print(f"比較エラー: {e}")

def analyze_glyph_smoothness(charString):
    """グリフの滑らかさを分析"""
    from fontTools.pens.recordingPen import RecordingPen
    import math
    
    try:
        pen = RecordingPen()
        charString.draw(pen)
        
        # 制御点の数を数える
        control_points = 0
        curve_commands = 0
        
        for cmd, pts in pen.value:
            if cmd in ['curveTo', 'qCurveTo']:
                curve_commands += 1
                control_points += len(pts) - 1  # 最後の点はオンカーブ
        
        # 滑らかさの推定（制御点の密度）
        total_commands = len(pen.value)
        smoothness = curve_commands / total_commands if total_commands > 0 else 0
        
        return {
            'control_points': control_points,
            'curve_commands': curve_commands,
            'smoothness': smoothness
        }
        
    except Exception as e:
        return {
            'control_points': 0,
            'curve_commands': 0,
            'smoothness': 0,
            'error': str(e)
        }

def main():
    print("ベジェ曲線対応角丸処理テスト")
    print("=" * 40)
    
    test_bezier_curve_fix()
    
    print("\n=== テスト結果の解釈 ===")
    print("1. 制御点数の変化:")
    print("   - 増加: ベジェ曲線が適切に処理されている")
    print("   - 減少: 制御点が失われている可能性")
    print()
    print("2. 滑らかさの変化:")
    print("   - 向上: 「カクカク」問題が改善")
    print("   - 低下: 処理により滑らかさが失われている")
    print()
    print("3. 期待される結果:")
    print("   - 制御点が適切に保持される")
    print("   - 滑らかさが向上または維持される")
    print("   - ベジェ曲線の実際の形状が考慮される")

if __name__ == "__main__":
    main()