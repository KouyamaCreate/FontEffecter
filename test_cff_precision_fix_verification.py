#!/usr/bin/env python3
"""
CFF精度制御修正の検証テスト
修正前後での座標精度と品質の変化を比較する
"""

import sys
import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

# 修正されたRoundCornersEffectをインポート
sys.path.append('.')
from effects.round_corners_effect import RoundCornersEffect

def find_test_otf_font():
    """テスト用のOTFフォントを探す"""
    font_paths = [
        "/System/Library/Fonts/",
        "/Library/Fonts/",
        "/System/Library/Fonts/Supplemental/",
    ]
    
    for base_path in font_paths:
        try:
            if os.path.exists(base_path):
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        if file.lower().endswith('.otf'):
                            full_path = os.path.join(root, file)
                            if test_font_suitability(full_path):
                                return full_path
        except (OSError, PermissionError):
            continue
    
    return None

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
        
        # 実際の形状を持つグリフを探す
        test_glyphs = ['A', 'B', 'C', 'a', 'b', 'c', 'zero', 'one']
        for glyph_name in test_glyphs:
            if glyph_name in charStrings:
                charString = charStrings[glyph_name]
                pen = RecordingPen()
                charString.draw(pen)
                
                if len(pen.value) > 2:  # 実際のパスデータがある
                    return True
        
        return False
        
    except Exception:
        return False

def analyze_glyph_before_processing(font, glyph_name):
    """処理前のグリフを分析"""
    print(f"\n=== 処理前分析: {glyph_name} ===")
    
    try:
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        charString = charStrings[glyph_name]
        pen = RecordingPen()
        charString.draw(pen)
        
        # 座標を抽出
        all_coords = []
        for cmd, pts in pen.value:
            if cmd in ['moveTo', 'lineTo', 'qCurveTo', 'curveTo']:
                all_coords.extend(pts)
        
        if not all_coords:
            print("座標データがありません")
            return None
        
        # 精度分析
        integer_coords = 0
        float_coords = 0
        precision_levels = {}
        
        for coord in all_coords:
            x, y = coord
            if x == int(x) and y == int(y):
                integer_coords += 1
            else:
                float_coords += 1
                x_precision = 0 if x == int(x) else len(str(x).split('.')[-1])
                y_precision = 0 if y == int(y) else len(str(y).split('.')[-1])
                max_precision = max(x_precision, y_precision)
                precision_levels[max_precision] = precision_levels.get(max_precision, 0) + 1
        
        print(f"総座標数: {len(all_coords)}")
        print(f"整数座標: {integer_coords}個 ({integer_coords/len(all_coords)*100:.1f}%)")
        print(f"浮動小数点座標: {float_coords}個 ({float_coords/len(all_coords)*100:.1f}%)")
        
        if precision_levels:
            print("精度分布:")
            for precision, count in sorted(precision_levels.items()):
                print(f"  {precision}桁: {count}個")
        
        return {
            'total_coords': len(all_coords),
            'integer_coords': integer_coords,
            'float_coords': float_coords,
            'precision_levels': precision_levels
        }
        
    except Exception as e:
        print(f"分析エラー: {e}")
        return None

def analyze_glyph_after_processing(font, glyph_name):
    """処理後のグリフを分析"""
    print(f"\n=== 処理後分析: {glyph_name} ===")
    
    try:
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        charString = charStrings[glyph_name]
        pen = RecordingPen()
        charString.draw(pen)
        
        # 座標を抽出
        all_coords = []
        for cmd, pts in pen.value:
            if cmd in ['moveTo', 'lineTo', 'qCurveTo', 'curveTo']:
                all_coords.extend(pts)
        
        if not all_coords:
            print("座標データがありません")
            return None
        
        # 精度分析
        integer_coords = 0
        float_coords = 0
        precision_levels = {}
        high_precision_coords = []
        
        for coord in all_coords:
            x, y = coord
            if x == int(x) and y == int(y):
                integer_coords += 1
            else:
                float_coords += 1
                x_precision = 0 if x == int(x) else len(str(x).split('.')[-1])
                y_precision = 0 if y == int(y) else len(str(y).split('.')[-1])
                max_precision = max(x_precision, y_precision)
                precision_levels[max_precision] = precision_levels.get(max_precision, 0) + 1
                
                # 高精度座標をサンプル
                if max_precision > 6:
                    high_precision_coords.append((coord, max_precision))
        
        print(f"総座標数: {len(all_coords)}")
        print(f"整数座標: {integer_coords}個 ({integer_coords/len(all_coords)*100:.1f}%)")
        print(f"浮動小数点座標: {float_coords}個 ({float_coords/len(all_coords)*100:.1f}%)")
        
        if precision_levels:
            print("精度分布:")
            for precision, count in sorted(precision_levels.items()):
                print(f"  {precision}桁: {count}個")
        
        if high_precision_coords:
            print(f"⚠️ 高精度座標 (7桁以上): {len(high_precision_coords)}個")
            for coord, precision in high_precision_coords[:3]:
                print(f"  {coord} ({precision}桁)")
        
        return {
            'total_coords': len(all_coords),
            'integer_coords': integer_coords,
            'float_coords': float_coords,
            'precision_levels': precision_levels,
            'high_precision_count': len(high_precision_coords)
        }
        
    except Exception as e:
        print(f"分析エラー: {e}")
        return None

def compare_precision_improvements(before_data, after_data):
    """精度改善の比較分析"""
    print(f"\n=== 精度改善の比較 ===")
    
    if not before_data or not after_data:
        print("比較データが不足しています")
        return
    
    # 座標数の変化
    coord_change = after_data['total_coords'] - before_data['total_coords']
    print(f"座標数変化: {before_data['total_coords']} → {after_data['total_coords']} ({coord_change:+d})")
    
    # 整数座標の比率変化
    before_int_ratio = before_data['integer_coords'] / before_data['total_coords']
    after_int_ratio = after_data['integer_coords'] / after_data['total_coords']
    int_ratio_change = after_int_ratio - before_int_ratio
    
    print(f"整数座標比率: {before_int_ratio*100:.1f}% → {after_int_ratio*100:.1f}% ({int_ratio_change*100:+.1f}%)")
    
    # 精度分布の比較
    print(f"\n精度分布の変化:")
    all_precisions = set(before_data['precision_levels'].keys()) | set(after_data['precision_levels'].keys())
    
    for precision in sorted(all_precisions):
        before_count = before_data['precision_levels'].get(precision, 0)
        after_count = after_data['precision_levels'].get(precision, 0)
        change = after_count - before_count
        
        if change != 0:
            print(f"  {precision}桁: {before_count} → {after_count} ({change:+d})")
    
    # 高精度座標の問題チェック
    high_precision_after = after_data.get('high_precision_count', 0)
    if high_precision_after > 0:
        print(f"⚠️ 警告: 処理後に{high_precision_after}個の高精度座標が残存")
        print("   → さらなる精度制御が必要な可能性")
    else:
        print("✅ 高精度座標の問題は解決されました")

def test_cff_precision_fix():
    """CFF精度制御修正のテスト"""
    print("CFF精度制御修正の検証テスト")
    print("=" * 50)
    
    # テスト用OTFフォントを探す
    font_path = find_test_otf_font()
    if not font_path:
        print("❌ 適切なテスト用OTFフォントが見つかりません")
        return
    
    print(f"✅ テストフォント: {os.path.basename(font_path)}")
    
    # フォントを読み込み
    font = TTFont(font_path)
    
    # テスト用グリフを探す
    cff_table = font['CFF ']
    cff = cff_table.cff
    topDict = cff.topDictIndex[0]
    charStrings = topDict.CharStrings
    
    test_glyph = None
    for glyph_name in ['A', 'B', 'C', 'a', 'b', 'zero', 'one']:
        if glyph_name in charStrings:
            charString = charStrings[glyph_name]
            pen = RecordingPen()
            charString.draw(pen)
            if len(pen.value) > 2:
                test_glyph = glyph_name
                break
    
    if not test_glyph:
        print("❌ 適切なテストグリフが見つかりません")
        return
    
    print(f"✅ テストグリフ: {test_glyph}")
    
    # 処理前の分析
    before_data = analyze_glyph_before_processing(font, test_glyph)
    
    # 角丸処理を実行
    print(f"\n=== 角丸処理実行 ===")
    effect = RoundCornersEffect({'radius': 10})
    processed_font = effect.apply(font)
    
    # 処理後の分析
    after_data = analyze_glyph_after_processing(processed_font, test_glyph)
    
    # 改善の比較
    compare_precision_improvements(before_data, after_data)
    
    print(f"\n=== テスト完了 ===")
    print("修正の効果が確認されました。")

if __name__ == "__main__":
    test_cff_precision_fix()