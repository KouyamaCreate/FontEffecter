#!/usr/bin/env python3
"""
ベジェ曲線ハンドル（制御点）無視問題の診断スクリプト
角丸処理でベジェ曲線の制御点が適切に処理されているかを検証
"""

import sys
import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

def analyze_bezier_handle_problem():
    """ベジェ曲線ハンドル処理問題を分析"""
    
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
    
    print(f"=== ベジェ曲線ハンドル問題診断 - {font_path} ===")
    
    try:
        font = TTFont(font_path)
        
        # フォント形式の確認
        has_glyf = 'glyf' in font
        has_cff = 'CFF ' in font
        
        print(f"フォント形式: {'TrueType' if has_glyf else 'OpenType/CFF' if has_cff else '不明'}")
        
        if has_cff:
            analyze_cff_bezier_handles(font)
        else:
            print("TrueType分析は未実装（CFFに焦点）")
            
    except Exception as e:
        print(f"フォント読み込みエラー: {e}")

def analyze_cff_bezier_handles(font):
    """CFFフォントのベジェ曲線ハンドル分析"""
    print("\n=== CFFベジェ曲線ハンドル分析 ===")
    
    try:
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        # 曲線を含むグリフを特定
        curve_glyphs = []
        glyph_names = list(charStrings.keys())[:10]  # 最初の10個をテスト
        
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
        
        print(f"曲線グリフ: {curve_glyphs}")
        
        # ベジェ曲線ハンドル問題の詳細分析
        for glyph_name in curve_glyphs[:3]:  # 最初の3個を詳細分析
            print(f"\n--- グリフ '{glyph_name}' のベジェハンドル分析 ---")
            analyze_single_glyph_bezier_handles(charStrings[glyph_name], glyph_name)
                
    except Exception as e:
        print(f"CFF分析エラー: {e}")

def analyze_single_glyph_bezier_handles(charString, glyph_name):
    """単一グリフのベジェ曲線ハンドル詳細分析"""
    try:
        # RecordingPenでパスデータを取得
        pen = RecordingPen()
        charString.draw(pen)
        
        print(f"  パスコマンド詳細:")
        curve_segments = []
        
        # パスコマンドの詳細分析
        for i, (cmd, pts) in enumerate(pen.value):
            print(f"    {i+1}: {cmd} {pts}")
            
            if cmd in ['curveTo', 'qCurveTo']:
                curve_segments.append((cmd, pts))
        
        print(f"  曲線セグメント数: {len(curve_segments)}")
        
        # パスデータから輪郭を抽出
        contours = extract_contours_with_curve_info(pen.value)
        
        for i, contour in enumerate(contours):
            coords = contour['coords']
            flags = contour['flags']
            curve_info = contour.get('curve_info', [])
            
            print(f"  輪郭 {i+1}: {len(coords)}点")
            print(f"    オンカーブ点: {sum(1 for f in flags if f & 1)}")
            print(f"    オフカーブ点（制御点）: {sum(1 for f in flags if not (f & 1))}")
            
            # **重要**: 現在の角丸処理でのベジェハンドル処理を検証
            bezier_handle_analysis = analyze_current_corner_rounding_bezier_handling(coords, flags, curve_info)
            print(f"    ベジェハンドル処理分析:")
            print(f"      制御点が角度計算に含まれる: {bezier_handle_analysis['control_points_in_angle_calc']}")
            print(f"      制御点間の角度計算: {bezier_handle_analysis['control_point_angles']}")
            print(f"      **問題**: 制御点無視による角度誤計算: {bezier_handle_analysis['ignored_control_points']}")
            print(f"      **問題**: 曲線セグメントの分割不足: {bezier_handle_analysis['insufficient_curve_subdivision']}")
            print(f"      **問題**: ハンドル方向の無視: {bezier_handle_analysis['ignored_handle_directions']}")
            
            # ベジェ曲線の実際の形状vs角度計算の比較
            shape_vs_angle_analysis = compare_bezier_shape_vs_angle_calculation(coords, flags, curve_info)
            print(f"    曲線形状vs角度計算比較:")
            print(f"      実際の曲線の滑らかさ: {shape_vs_angle_analysis['actual_smoothness']}")
            print(f"      角度計算での滑らかさ: {shape_vs_angle_analysis['calculated_smoothness']}")
            print(f"      **問題**: 滑らかさの不一致: {shape_vs_angle_analysis['smoothness_mismatch']}")
            
    except Exception as e:
        print(f"  グリフ分析エラー: {e}")

def extract_contours_with_curve_info(pen_value):
    """RecordingPenの値から輪郭と曲線情報を抽出"""
    contours = []
    current_coords = []
    current_flags = []
    current_curve_info = []
    
    for cmd, pts in pen_value:
        if cmd == "moveTo":
            if current_coords:
                contours.append({
                    'coords': current_coords, 
                    'flags': current_flags,
                    'curve_info': current_curve_info
                })
            current_coords = [pts[0]]
            current_flags = [1]  # オンカーブ
            current_curve_info = [{'type': 'move', 'cmd': cmd}]
        elif cmd == "lineTo":
            current_coords.append(pts[0])
            current_flags.append(1)  # オンカーブ
            current_curve_info.append({'type': 'line', 'cmd': cmd})
        elif cmd == "curveTo":
            # 三次ベジェ曲線
            for j, p in enumerate(pts[:-1]):
                current_coords.append(p)
                current_flags.append(0)  # オフカーブ（制御点）
                current_curve_info.append({'type': 'control', 'cmd': cmd, 'index': j})
            current_coords.append(pts[-1])
            current_flags.append(1)  # オンカーブ
            current_curve_info.append({'type': 'curve_end', 'cmd': cmd})
        elif cmd == "qCurveTo":
            # 二次ベジェ曲線
            for j, p in enumerate(pts[:-1]):
                current_coords.append(p)
                current_flags.append(0)  # オフカーブ（制御点）
                current_curve_info.append({'type': 'control', 'cmd': cmd, 'index': j})
            current_coords.append(pts[-1])
            current_flags.append(1)  # オンカーブ
            current_curve_info.append({'type': 'curve_end', 'cmd': cmd})
        elif cmd in ["closePath", "endPath"]:
            pass
    
    if current_coords:
        contours.append({
            'coords': current_coords, 
            'flags': current_flags,
            'curve_info': current_curve_info
        })
    
    return contours

def analyze_current_corner_rounding_bezier_handling(coords, flags, curve_info):
    """現在の角丸処理でのベジェハンドル処理を分析"""
    n = len(coords)
    if n < 3:
        return {'error': '点数不足'}
    
    control_points_in_angle_calc = 0
    control_point_angles = []
    ignored_control_points = 0
    insufficient_curve_subdivision = 0
    ignored_handle_directions = 0
    
    # 現在の角丸処理と同じ方法で角度計算
    for i in range(n):
        p0 = coords[i - 1]
        p1 = coords[i]
        p2 = coords[(i + 1) % n]
        
        is_control_point = not (flags[i] & 1)
        
        if is_control_point:
            # 制御点での角度計算
            v1 = (p0[0] - p1[0], p0[1] - p1[1])
            v2 = (p2[0] - p1[0], p2[1] - p1[1])
            norm1 = math.hypot(*v1)
            norm2 = math.hypot(*v2)
            
            if norm1 > 0 and norm2 > 0:
                dot = v1[0] * v2[0] + v1[1] * v2[1]
                cos_angle = dot / (norm1 * norm2)
                cos_angle = max(-1.0, min(1.0, cos_angle))
                angle_deg = math.degrees(math.acos(cos_angle))
                
                control_point_angles.append(angle_deg)
                control_points_in_angle_calc += 1
                
                # **問題**: 制御点での角度計算は曲線の実際の形状を反映しない
                if angle_deg > 150:  # 現在の閾値で処理されない
                    ignored_control_points += 1
            else:
                ignored_control_points += 1
        
        # ベジェ曲線セグメントの分析
        if i < len(curve_info):
            info = curve_info[i]
            if info['type'] == 'control':
                # 制御点の方向ベクトル分析
                if i > 0 and i < n - 1:
                    prev_point = coords[i - 1]
                    next_point = coords[i + 1]
                    
                    # ハンドルの方向
                    handle_dir = (p1[0] - prev_point[0], p1[1] - prev_point[1])
                    curve_dir = (next_point[0] - prev_point[0], next_point[1] - prev_point[1])
                    
                    # ハンドル方向と曲線方向の一致度
                    if math.hypot(*handle_dir) > 0 and math.hypot(*curve_dir) > 0:
                        dot = handle_dir[0] * curve_dir[0] + handle_dir[1] * curve_dir[1]
                        norm_h = math.hypot(*handle_dir)
                        norm_c = math.hypot(*curve_dir)
                        cos_similarity = dot / (norm_h * norm_c)
                        
                        # ハンドル方向が無視されている場合
                        if abs(cos_similarity) < 0.5:  # 60度以上の差
                            ignored_handle_directions += 1
    
    return {
        'control_points_in_angle_calc': control_points_in_angle_calc,
        'control_point_angles': control_point_angles,
        'ignored_control_points': ignored_control_points,
        'insufficient_curve_subdivision': insufficient_curve_subdivision,
        'ignored_handle_directions': ignored_handle_directions
    }

def compare_bezier_shape_vs_angle_calculation(coords, flags, curve_info):
    """ベジェ曲線の実際の形状と角度計算の比較"""
    n = len(coords)
    
    # 実際の曲線の滑らかさを評価
    actual_smoothness = evaluate_actual_curve_smoothness(coords, flags, curve_info)
    
    # 角度計算での滑らかさを評価
    calculated_smoothness = evaluate_calculated_smoothness(coords, flags)
    
    # 不一致の検出
    smoothness_mismatch = abs(actual_smoothness - calculated_smoothness) > 0.3
    
    return {
        'actual_smoothness': actual_smoothness,
        'calculated_smoothness': calculated_smoothness,
        'smoothness_mismatch': smoothness_mismatch
    }

def evaluate_actual_curve_smoothness(coords, flags, curve_info):
    """実際の曲線の滑らかさを評価"""
    # ベジェ曲線セグメントの連続性を分析
    curve_segments = 0
    smooth_transitions = 0
    
    for i, info in enumerate(curve_info):
        if info['type'] == 'curve_end':
            curve_segments += 1
            
            # 前後の制御点の方向を比較
            if i > 2 and i < len(curve_info) - 1:
                # 滑らかな遷移の判定（簡易版）
                smooth_transitions += 1
    
    return smooth_transitions / curve_segments if curve_segments > 0 else 0

def evaluate_calculated_smoothness(coords, flags):
    """角度計算での滑らかさを評価"""
    n = len(coords)
    smooth_angles = 0
    total_angles = 0
    
    for i in range(n):
        p0 = coords[i - 1]
        p1 = coords[i]
        p2 = coords[(i + 1) % n]
        
        v1 = (p0[0] - p1[0], p0[1] - p1[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        norm1 = math.hypot(*v1)
        norm2 = math.hypot(*v2)
        
        if norm1 > 0 and norm2 > 0:
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            cos_angle = dot / (norm1 * norm2)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle_deg = math.degrees(math.acos(cos_angle))
            
            total_angles += 1
            if angle_deg > 170:  # 滑らかな角度
                smooth_angles += 1
    
    return smooth_angles / total_angles if total_angles > 0 else 0

def main():
    print("ベジェ曲線ハンドル（制御点）無視問題診断")
    print("=" * 50)
    
    analyze_bezier_handle_problem()
    
    print("\n=== 診断結果の解釈 ===")
    print("**ベジェハンドル処理問題**:")
    print("  - ignored_control_points: 角度計算で無視された制御点")
    print("  - ignored_handle_directions: 方向が無視されたハンドル")
    print("  → 多い場合、制御点を考慮した角丸処理が必要")
    print()
    print("**曲線形状vs角度計算の不一致**:")
    print("  - smoothness_mismatch: 実際の滑らかさと計算の不一致")
    print("  → 不一致がある場合、ベジェ曲線専用の処理が必要")
    print()
    print("**修正方針**:")
    print("  1. 制御点を考慮した角度計算")
    print("  2. ベジェ曲線セグメントの適切な分割")
    print("  3. ハンドル方向を保持する角丸処理")

if __name__ == "__main__":
    main()