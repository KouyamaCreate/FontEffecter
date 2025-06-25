#!/usr/bin/env python3
"""
利用可能な曲線グリフの分析スクリプト
実際のグリフで角度閾値とT2CharString座標精度の問題を診断
"""

import sys
import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

def analyze_available_curve_glyphs():
    """利用可能な曲線グリフを分析"""
    
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
    
    print(f"=== 曲線グリフ診断 - {font_path} ===")
    
    try:
        font = TTFont(font_path)
        
        # フォント形式の確認
        has_glyf = 'glyf' in font
        has_cff = 'CFF ' in font
        
        print(f"フォント形式: {'TrueType' if has_glyf else 'OpenType/CFF' if has_cff else '不明'}")
        
        if has_cff:
            analyze_cff_available_glyphs(font)
        elif has_glyf:
            analyze_truetype_available_glyphs(font)
        else:
            print("サポートされていないフォント形式です")
            
    except Exception as e:
        print(f"フォント読み込みエラー: {e}")

def analyze_cff_available_glyphs(font):
    """CFFフォントの利用可能グリフ分析"""
    print("\n=== CFF利用可能グリフ分析 ===")
    
    try:
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        print(f"総グリフ数: {len(charStrings)}")
        
        # 最初の10個のグリフを表示
        glyph_names = list(charStrings.keys())[:20]
        print(f"最初の20個のグリフ: {glyph_names}")
        
        # 曲線を含むグリフを特定
        curve_glyphs = []
        
        for glyph_name in glyph_names:
            try:
                charString = charStrings[glyph_name]
                pen = RecordingPen()
                charString.draw(pen)
                
                # 曲線コマンドを検出
                has_curves = any(cmd in ['curveTo', 'qCurveTo'] for cmd, _ in pen.value)
                
                if has_curves:
                    curve_glyphs.append(glyph_name)
                    
            except Exception as e:
                print(f"グリフ '{glyph_name}' の分析エラー: {e}")
        
        print(f"\n曲線を含むグリフ: {curve_glyphs}")
        
        # 曲線グリフの詳細分析（最初の5個）
        for glyph_name in curve_glyphs[:5]:
            print(f"\n--- グリフ '{glyph_name}' の詳細分析 ---")
            analyze_single_cff_glyph_detailed(charStrings[glyph_name], glyph_name)
                
    except Exception as e:
        print(f"CFF分析エラー: {e}")

def analyze_single_cff_glyph_detailed(charString, glyph_name):
    """単一CFFグリフの詳細分析（角度問題に焦点）"""
    try:
        # RecordingPenでパスデータを取得
        pen = RecordingPen()
        charString.draw(pen)
        
        print(f"  パスコマンド数: {len(pen.value)}")
        
        # パスコマンドの詳細表示
        curve_commands = []
        for cmd, pts in pen.value:
            if cmd in ['curveTo', 'qCurveTo']:
                curve_commands.append((cmd, pts))
        
        print(f"  曲線コマンド数: {len(curve_commands)}")
        
        # パスデータから輪郭を抽出
        contours = extract_contours_from_recording_pen(pen.value)
        
        print(f"  輪郭数: {len(contours)}")
        
        for i, contour in enumerate(contours):
            coords = contour['coords']
            flags = contour['flags']
            
            print(f"  輪郭 {i+1}: {len(coords)}点")
            
            # **重要**: 角度閾値問題の詳細分析
            angle_analysis = analyze_angle_threshold_problem(coords, flags)
            print(f"    角度閾値問題分析:")
            print(f"      現在の閾値(150度)で処理される角: {angle_analysis['current_threshold_150']}")
            print(f"      現在の閾値(160度)で処理される角: {angle_analysis['current_threshold_160']}")
            print(f"      現在の閾値(170度)で処理される角: {angle_analysis['current_threshold_170']}")
            print(f"      直線判定(178度)される角: {angle_analysis['straight_line_178']}")
            print(f"      **問題**: 170-178度の角: {angle_analysis['problem_range_170_178']}")
            print(f"      **問題**: 175-178度の角: {angle_analysis['problem_range_175_178']}")
            print(f"      最小角度: {angle_analysis['min_angle']:.2f}度")
            print(f"      最大角度: {angle_analysis['max_angle']:.2f}度")
            
            # **重要**: T2CharString座標精度問題の分析
            precision_analysis = analyze_t2charstring_precision_problem(coords)
            print(f"    T2CharString座標精度問題分析:")
            print(f"      整数座標の割合: {precision_analysis['integer_ratio']:.2%}")
            print(f"      浮動小数点座標の割合: {precision_analysis['float_ratio']:.2%}")
            print(f"      最大小数点桁数: {precision_analysis['max_decimal_places']}")
            print(f"      **問題**: 混在座標: {precision_analysis['mixed_precision']}")
            print(f"      **問題**: 高精度座標: {precision_analysis['high_precision_count']}")
            
            # 曲線の滑らかさ分析
            smoothness_analysis = analyze_curve_smoothness(coords, flags)
            print(f"    曲線滑らかさ分析:")
            print(f"      制御点の割合: {smoothness_analysis['control_point_ratio']:.2%}")
            print(f"      連続曲線セグメント: {smoothness_analysis['continuous_curve_segments']}")
            print(f"      **問題**: 急激な方向変化: {smoothness_analysis['sharp_direction_changes']}")
            
    except Exception as e:
        print(f"  グリフ分析エラー: {e}")

def analyze_angle_threshold_problem(coords, flags):
    """角度閾値問題の詳細分析"""
    n = len(coords)
    if n < 3:
        return {'error': '点数不足'}
    
    angles = []
    threshold_counts = {
        150: 0, 160: 0, 170: 0, 175: 0, 178: 0
    }
    
    problem_range_170_178 = 0  # 170-178度の「問題範囲」
    problem_range_175_178 = 0  # 175-178度の「高問題範囲」
    
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
        for threshold in [150, 160, 170, 175, 178]:
            if angle_deg < threshold:
                threshold_counts[threshold] += 1
        
        # 問題範囲の検出
        if 170 <= angle_deg < 178:
            problem_range_170_178 += 1
        if 175 <= angle_deg < 178:
            problem_range_175_178 += 1
    
    return {
        'current_threshold_150': threshold_counts[150],
        'current_threshold_160': threshold_counts[160],
        'current_threshold_170': threshold_counts[170],
        'straight_line_178': len(angles) - threshold_counts[178],
        'problem_range_170_178': problem_range_170_178,
        'problem_range_175_178': problem_range_175_178,
        'min_angle': min(angles) if angles else 0,
        'max_angle': max(angles) if angles else 0,
        'total_angles': len(angles)
    }

def analyze_t2charstring_precision_problem(coords):
    """T2CharString座標精度問題の分析"""
    integer_count = 0
    float_count = 0
    high_precision_count = 0
    max_decimal_places = 0
    
    for x, y in coords:
        # X座標の精度分析
        if x == int(x):
            integer_count += 1
        else:
            float_count += 1
            decimal_str = str(abs(x)).split('.')
            if len(decimal_str) > 1:
                decimal_places = len(decimal_str[1])
                max_decimal_places = max(max_decimal_places, decimal_places)
                if decimal_places > 3:  # 3桁以上の小数点は高精度
                    high_precision_count += 1
        
        # Y座標の精度分析
        if y == int(y):
            integer_count += 1
        else:
            float_count += 1
            decimal_str = str(abs(y)).split('.')
            if len(decimal_str) > 1:
                decimal_places = len(decimal_str[1])
                max_decimal_places = max(max_decimal_places, decimal_places)
                if decimal_places > 3:
                    high_precision_count += 1
    
    total = len(coords) * 2
    
    return {
        'integer_ratio': integer_count / total if total > 0 else 0,
        'float_ratio': float_count / total if total > 0 else 0,
        'max_decimal_places': max_decimal_places,
        'mixed_precision': integer_count > 0 and float_count > 0,
        'high_precision_count': high_precision_count
    }

def analyze_curve_smoothness(coords, flags):
    """曲線の滑らかさ分析"""
    n = len(coords)
    control_points = sum(1 for f in flags if not (f & 1))
    
    # 連続する曲線セグメントを検出
    continuous_segments = 0
    current_segment_length = 0
    
    # 急激な方向変化を検出
    sharp_changes = 0
    
    for i in range(n):
        is_control_point = not (flags[i] & 1)
        
        if is_control_point:
            current_segment_length += 1
        else:
            if current_segment_length > 0:
                continuous_segments += 1
                current_segment_length = 0
        
        # 方向変化の分析（3点での角度変化）
        if i >= 2:
            p0 = coords[i - 2]
            p1 = coords[i - 1]
            p2 = coords[i]
            
            # 2つのベクトルの角度差
            v1 = (p1[0] - p0[0], p1[1] - p0[1])
            v2 = (p2[0] - p1[0], p2[1] - p1[1])
            
            norm1 = math.hypot(*v1)
            norm2 = math.hypot(*v2)
            
            if norm1 > 0 and norm2 > 0:
                dot = v1[0] * v2[0] + v1[1] * v2[1]
                cos_angle = dot / (norm1 * norm2)
                cos_angle = max(-1.0, min(1.0, cos_angle))
                angle_deg = math.degrees(math.acos(cos_angle))
                
                # 急激な変化（90度以下）
                if angle_deg < 90:
                    sharp_changes += 1
    
    return {
        'control_point_ratio': control_points / n if n > 0 else 0,
        'continuous_curve_segments': continuous_segments,
        'sharp_direction_changes': sharp_changes
    }

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

def analyze_truetype_available_glyphs(font):
    """TrueTypeフォントの利用可能グリフ分析"""
    print("\n=== TrueType利用可能グリフ分析 ===")
    print("TrueType分析は未実装（CFFに焦点）")

def main():
    print("曲線グリフ「カクカク」問題診断（実際のグリフ使用）")
    print("=" * 60)
    
    analyze_available_curve_glyphs()
    
    print("\n=== 診断結果の解釈 ===")
    print("**角度閾値問題**:")
    print("  - problem_range_170_178: 現在処理されない170-178度の角")
    print("  - problem_range_175_178: 特に問題となる175-178度の角")
    print("  → これらが多い場合、閾値を180度近くまで上げる必要")
    print()
    print("**T2CharString座標精度問題**:")
    print("  - mixed_precision: 整数と浮動小数点の混在")
    print("  - high_precision_count: 高精度（3桁以上小数点）座標")
    print("  → 混在や高精度が多い場合、座標正規化が必要")
    print()
    print("**曲線滑らかさ問題**:")
    print("  - sharp_direction_changes: 急激な方向変化")
    print("  - continuous_curve_segments: 連続曲線セグメント")
    print("  → 急激な変化が多い場合、角丸処理が「カクカク」の原因")

if __name__ == "__main__":
    main()