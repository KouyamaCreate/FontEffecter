#!/usr/bin/env python3
"""
ひらがな曲線グリフの「カクカク」問題診断スクリプト
角度閾値とT2CharString座標精度の問題を詳細分析
"""

import sys
import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

def analyze_hiragana_curves():
    """ひらがなグリフの曲線特性を分析"""
    
    # テスト用フォントファイルを探す
    test_fonts = [
        'output_final_fixed.otf',
        'output_otf_rounded_fixed.otf', 
        'output_rounded.otf'
    ]
    
    font_path = None
    for font_file in test_fonts:
        if os.path.exists(font_file):
            font_path = font_file
            break
    
    if not font_path:
        print("エラー: テスト用フォントファイルが見つかりません")
        return
    
    print(f"=== ひらがな曲線診断 - {font_path} ===")
    
    try:
        font = TTFont(font_path)
        
        # フォント形式の確認
        has_glyf = 'glyf' in font
        has_cff = 'CFF ' in font
        
        print(f"フォント形式: {'TrueType' if has_glyf else 'OpenType/CFF' if has_cff else '不明'}")
        
        if has_cff:
            analyze_cff_hiragana_curves(font)
        elif has_glyf:
            analyze_truetype_hiragana_curves(font)
        else:
            print("サポートされていないフォント形式です")
            
    except Exception as e:
        print(f"フォント読み込みエラー: {e}")

def analyze_cff_hiragana_curves(font):
    """CFFフォントのひらがな曲線分析"""
    print("\n=== CFFひらがな曲線分析 ===")
    
    try:
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        # ひらがなのテスト文字（Unicode範囲: U+3042-U+3096）
        hiragana_test_chars = ['あ', 'か', 'さ', 'た', 'な', 'は', 'ま', 'や', 'ら', 'わ']
        
        for char in hiragana_test_chars:
            unicode_val = ord(char)
            glyph_name = None
            
            # グリフ名を探す
            if 'cmap' in font:
                for table in font['cmap'].tables:
                    if unicode_val in table.cmap:
                        glyph_name = table.cmap[unicode_val]
                        break
            
            if glyph_name and glyph_name in charStrings:
                print(f"\n--- 文字 '{char}' (U+{unicode_val:04X}, {glyph_name}) ---")
                analyze_single_cff_glyph(charStrings[glyph_name], glyph_name)
            else:
                print(f"文字 '{char}' のグリフが見つかりません")
                
    except Exception as e:
        print(f"CFF分析エラー: {e}")

def analyze_single_cff_glyph(charString, glyph_name):
    """単一CFFグリフの詳細分析"""
    try:
        # RecordingPenでパスデータを取得
        pen = RecordingPen()
        charString.draw(pen)
        
        # パスデータから輪郭を抽出
        contours = extract_contours_from_recording_pen(pen.value)
        
        print(f"  輪郭数: {len(contours)}")
        
        for i, contour in enumerate(contours):
            coords = contour['coords']
            flags = contour['flags']
            
            print(f"  輪郭 {i+1}: {len(coords)}点")
            
            # 座標精度分析
            precision_analysis = analyze_coordinate_precision(coords)
            print(f"    座標精度: {precision_analysis}")
            
            # 角度分析（詳細）
            angle_analysis = analyze_curve_angles_detailed(coords, flags)
            print(f"    角度分析: {angle_analysis}")
            
            # 曲線特性分析
            curve_analysis = analyze_curve_characteristics(coords, flags)
            print(f"    曲線特性: {curve_analysis}")
            
    except Exception as e:
        print(f"  グリフ分析エラー: {e}")

def extract_contours_from_recording_pen(pen_value):
    """RecordingPenの値から輪郭を抽出"""
    contours = []
    current_coords = []
    current_flags = []
    
    for cmd, pts in pen_value:
        if cmd == "moveTo":
            if current_coords:
                contours.append({'coords': current_coords, 'flags': current_flags})
            current_coords = [pts[0]]
            current_flags = [1]  # オンカーブ
        elif cmd == "lineTo":
            current_coords.append(pts[0])
            current_flags.append(1)  # オンカーブ
        elif cmd == "curveTo":
            # 三次ベジェ曲線を二次ベジェに近似
            for p in pts[:-1]:
                current_coords.append(p)
                current_flags.append(0)  # オフカーブ
            current_coords.append(pts[-1])
            current_flags.append(1)  # オンカーブ
        elif cmd == "qCurveTo":
            # 二次ベジェ曲線
            for p in pts[:-1]:
                current_coords.append(p)
                current_flags.append(0)  # オフカーブ
            current_coords.append(pts[-1])
            current_flags.append(1)  # オンカーブ
        elif cmd in ["closePath", "endPath"]:
            pass
    
    if current_coords:
        contours.append({'coords': current_coords, 'flags': current_flags})
    
    return contours

def analyze_coordinate_precision(coords):
    """座標精度を分析"""
    integer_count = 0
    float_count = 0
    max_decimal_places = 0
    
    for x, y in coords:
        # X座標
        if x == int(x):
            integer_count += 1
        else:
            float_count += 1
            decimal_str = str(x).split('.')
            if len(decimal_str) > 1:
                max_decimal_places = max(max_decimal_places, len(decimal_str[1]))
        
        # Y座標
        if y == int(y):
            integer_count += 1
        else:
            float_count += 1
            decimal_str = str(y).split('.')
            if len(decimal_str) > 1:
                max_decimal_places = max(max_decimal_places, len(decimal_str[1]))
    
    total = len(coords) * 2
    return {
        'integer_ratio': integer_count / total if total > 0 else 0,
        'float_ratio': float_count / total if total > 0 else 0,
        'max_decimal_places': max_decimal_places
    }

def analyze_curve_angles_detailed(coords, flags):
    """詳細な角度分析"""
    n = len(coords)
    if n < 3:
        return {'error': '点数不足'}
    
    angles = []
    straight_line_count = 0
    curve_count = 0
    
    # 現在の角度閾値
    current_thresholds = [150, 160, 170, 175, 178, 179]
    threshold_counts = {t: 0 for t in current_thresholds}
    
    for i in range(n):
        p0 = coords[i - 1]
        p1 = coords[i]
        p2 = coords[(i + 1) % n]
        
        # ベクトル計算
        v1 = (p0[0] - p1[0], p0[1] - p1[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        norm1 = math.hypot(*v1)
        norm2 = math.hypot(*v2)
        
        if norm1 == 0 or norm2 == 0:
            continue
        
        # 角度計算
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        cos_angle = dot / (norm1 * norm2)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        angle_deg = math.degrees(math.acos(cos_angle))
        
        angles.append(angle_deg)
        
        # 閾値別カウント
        for threshold in current_thresholds:
            if angle_deg < threshold:
                threshold_counts[threshold] += 1
        
        # 直線・曲線判定
        if angle_deg >= 178:
            straight_line_count += 1
        else:
            curve_count += 1
    
    return {
        'total_angles': len(angles),
        'min_angle': min(angles) if angles else 0,
        'max_angle': max(angles) if angles else 0,
        'avg_angle': sum(angles) / len(angles) if angles else 0,
        'straight_lines': straight_line_count,
        'curves': curve_count,
        'threshold_counts': threshold_counts
    }

def analyze_curve_characteristics(coords, flags):
    """曲線特性を分析"""
    n = len(coords)
    on_curve_count = sum(1 for f in flags if f & 1)
    off_curve_count = n - on_curve_count
    
    # 連続する曲線セグメントを検出
    curve_segments = 0
    in_curve_segment = False
    
    for i in range(n):
        is_on_curve = flags[i] & 1
        
        if not is_on_curve:  # オフカーブ点（制御点）
            if not in_curve_segment:
                curve_segments += 1
                in_curve_segment = True
        else:
            in_curve_segment = False
    
    return {
        'total_points': n,
        'on_curve_points': on_curve_count,
        'off_curve_points': off_curve_count,
        'curve_segments': curve_segments,
        'curve_ratio': off_curve_count / n if n > 0 else 0
    }

def analyze_truetype_hiragana_curves(font):
    """TrueTypeフォントのひらがな曲線分析"""
    print("\n=== TrueTypeひらがな曲線分析 ===")
    print("TrueType分析は未実装（CFFに焦点）")

def main():
    print("ひらがな曲線グリフ「カクカク」問題診断")
    print("=" * 50)
    
    analyze_hiragana_curves()
    
    print("\n=== 診断結果の解釈 ===")
    print("1. 角度分析:")
    print("   - threshold_counts: 各閾値で処理される角の数")
    print("   - 現在の150-175度閾値で処理されない角が多い場合、閾値調整が必要")
    print("   - min_angle/max_angleで実際の角度範囲を確認")
    print()
    print("2. 座標精度分析:")
    print("   - float_ratio: 浮動小数点座標の割合")
    print("   - max_decimal_places: 最大小数点桁数")
    print("   - 高精度座標が多い場合、精度制御が必要")
    print()
    print("3. 曲線特性分析:")
    print("   - curve_ratio: 制御点の割合")
    print("   - curve_segments: 連続曲線セグメント数")
    print("   - 曲線が多い場合、曲線専用処理が必要")

if __name__ == "__main__":
    main()