#!/usr/bin/env python3
"""
OTFフォント専用の詳細分析スクリプト
CFFフォントの座標精度と角丸処理の品質問題を特定する
"""

import sys
import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

def find_otf_fonts_with_glyphs():
    """実際の形状を持つOTFフォントを探す"""
    print("OTFフォントを詳細検索中...")
    
    # より広範囲のフォントパスを探索
    font_paths = [
        "/System/Library/Fonts/",
        "/Library/Fonts/",
        "/System/Library/Fonts/Supplemental/",
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font6/",
    ]
    
    otf_fonts = []
    
    for base_path in font_paths:
        try:
            if os.path.exists(base_path):
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        if file.lower().endswith('.otf'):
                            full_path = os.path.join(root, file)
                            otf_fonts.append(full_path)
        except (OSError, PermissionError):
            continue
    
    print(f"発見されたOTFファイル: {len(otf_fonts)}個")
    
    # 各OTFフォントで実際の形状を持つグリフを探す
    for font_path in otf_fonts:
        try:
            result = analyze_otf_font_detailed(font_path)
            if result:
                return result
        except Exception as e:
            print(f"OTF分析エラー: {os.path.basename(font_path)} - {e}")
            continue
    
    return None

def analyze_otf_font_detailed(font_path):
    """OTFフォントの詳細分析"""
    try:
        font = TTFont(font_path)
        
        if 'CFF ' not in font:
            return None
        
        print(f"\n🔍 分析中: {os.path.basename(font_path)}")
        
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        print(f"  グリフ数: {len(charStrings)}")
        
        # PrivateDict情報
        if hasattr(topDict, 'Private') and topDict.Private:
            private = topDict.Private
            print(f"  PrivateDict: あり")
            if hasattr(private, 'nominalWidthX'):
                print(f"    nominalWidthX: {private.nominalWidthX}")
            if hasattr(private, 'defaultWidthX'):
                print(f"    defaultWidthX: {private.defaultWidthX}")
        
        # 実際の形状を持つグリフを探す
        test_glyphs = ['A', 'B', 'C', 'D', 'E', 'a', 'b', 'c', 'd', 'e', 
                      'zero', 'one', 'two', 'three', 'four', 'five',
                      'period', 'comma', 'question', 'exclam']
        
        for glyph_name in test_glyphs:
            if glyph_name in charStrings:
                charString = charStrings[glyph_name]
                pen = RecordingPen()
                charString.draw(pen)
                
                if len(pen.value) > 2:  # 実際のパスデータがある
                    print(f"  ✅ 形状あり: {glyph_name} ({len(pen.value)}コマンド)")
                    return {
                        'font_path': font_path,
                        'glyph_name': glyph_name,
                        'font': font,
                        'pen_data': pen.value
                    }
        
        print(f"  ❌ 適切なグリフが見つかりません")
        return None
        
    except Exception as e:
        print(f"  エラー: {e}")
        return None

def analyze_cff_coordinate_precision(pen_value, glyph_name):
    """CFFグリフの座標精度を詳細分析"""
    print(f"\n=== CFF座標精度分析: {glyph_name} ===")
    
    all_coords = []
    command_analysis = []
    
    for i, (cmd, pts) in enumerate(pen_value):
        command_analysis.append({
            'index': i,
            'command': cmd,
            'points': pts,
            'point_count': len(pts)
        })
        
        if cmd in ['moveTo', 'lineTo']:
            all_coords.extend(pts)
        elif cmd in ['qCurveTo', 'curveTo']:
            all_coords.extend(pts)
    
    print(f"総コマンド数: {len(pen_value)}")
    print(f"総座標数: {len(all_coords)}")
    
    # コマンド別分析
    cmd_counts = {}
    for analysis in command_analysis:
        cmd = analysis['command']
        cmd_counts[cmd] = cmd_counts.get(cmd, 0) + 1
    
    print(f"コマンド分布:")
    for cmd, count in cmd_counts.items():
        print(f"  {cmd}: {count}個")
    
    if not all_coords:
        print("座標データがありません")
        return None
    
    # 座標精度の詳細分析
    integer_coords = 0
    float_coords = 0
    precision_distribution = {}
    high_precision_coords = []
    
    for coord in all_coords:
        x, y = coord
        
        # X座標の精度分析
        x_is_int = (x == int(x))
        y_is_int = (y == int(y))
        
        if x_is_int and y_is_int:
            integer_coords += 1
        else:
            float_coords += 1
            
            # 精度レベルを計算
            x_precision = 0 if x_is_int else len(str(x).split('.')[-1])
            y_precision = 0 if y_is_int else len(str(y).split('.')[-1])
            max_precision = max(x_precision, y_precision)
            
            precision_distribution[max_precision] = precision_distribution.get(max_precision, 0) + 1
            
            # 高精度座標をサンプル
            if max_precision > 3:
                high_precision_coords.append((coord, max_precision))
    
    print(f"\n座標精度分析:")
    print(f"  整数座標: {integer_coords}個 ({integer_coords/len(all_coords)*100:.1f}%)")
    print(f"  浮動小数点座標: {float_coords}個 ({float_coords/len(all_coords)*100:.1f}%)")
    
    if precision_distribution:
        print(f"  精度分布:")
        for precision, count in sorted(precision_distribution.items()):
            print(f"    {precision}桁: {count}個")
    
    if high_precision_coords:
        print(f"  高精度座標の例 (4桁以上):")
        for coord, precision in high_precision_coords[:5]:
            print(f"    {coord} ({precision}桁)")
    
    # 座標範囲
    x_coords = [coord[0] for coord in all_coords]
    y_coords = [coord[1] for coord in all_coords]
    
    print(f"\n座標範囲:")
    print(f"  X: {min(x_coords):.6f} ～ {max(x_coords):.6f}")
    print(f"  Y: {min(y_coords):.6f} ～ {max(y_coords):.6f}")
    
    return {
        'coords': all_coords,
        'integer_ratio': integer_coords / len(all_coords),
        'float_ratio': float_coords / len(all_coords),
        'precision_distribution': precision_distribution,
        'coordinate_range': {
            'x_min': min(x_coords), 'x_max': max(x_coords),
            'y_min': min(y_coords), 'y_max': max(y_coords)
        }
    }

def simulate_cff_corner_rounding(pen_value, radius=10):
    """CFFデータで角丸処理をシミュレートし、品質劣化を分析"""
    print(f"\n=== CFF角丸処理シミュレート (radius={radius}) ===")
    
    # RecordingPenデータを輪郭に変換
    contours = convert_pen_to_contours(pen_value)
    
    if not contours:
        print("輪郭データの変換に失敗")
        return None
    
    print(f"変換された輪郭数: {len(contours)}")
    
    original_total_points = sum(len(c['coords']) for c in contours)
    print(f"処理前総点数: {original_total_points}")
    
    # 各輪郭で角丸処理をシミュレート
    quality_metrics = {
        'original_points': original_total_points,
        'rounded_points': 0,
        'corners_processed': 0,
        'precision_changes': [],
        'coordinate_shifts': []
    }
    
    for i, contour in enumerate(contours):
        coords = contour['coords']
        n = len(coords)
        
        if n < 3:
            quality_metrics['rounded_points'] += n
            continue
        
        print(f"\n輪郭{i}: {n}点を処理")
        
        new_coords = []
        corners_in_contour = 0
        
        for j in range(n):
            p0 = coords[j - 1]
            p1 = coords[j]
            p2 = coords[(j + 1) % n]
            
            # ベクトル計算
            v1 = (p0[0] - p1[0], p0[1] - p1[1])
            v2 = (p2[0] - p1[0], p2[1] - p1[1])
            norm1 = math.hypot(*v1)
            norm2 = math.hypot(*v2)
            
            if norm1 == 0 or norm2 == 0:
                new_coords.append(p1)
                continue
            
            # 角度計算
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            cos_angle = dot / (norm1 * norm2)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle_deg = math.degrees(math.acos(cos_angle))
            
            # 角丸判定
            if angle_deg < 140:
                # 角丸処理
                l1 = min(radius, norm1 * 0.5)
                l2 = min(radius, norm2 * 0.5)
                
                T1 = (p1[0] + (p0[0] - p1[0]) * l1 / norm1, 
                      p1[1] + (p0[1] - p1[1]) * l1 / norm1)
                T2 = (p1[0] + (p2[0] - p1[0]) * l2 / norm2, 
                      p1[1] + (p2[1] - p1[1]) * l2 / norm2)
                
                new_coords.extend([T1, p1, T2])
                corners_in_contour += 1
                
                # 精度変化を記録
                original_precision = get_coordinate_precision(p1)
                t1_precision = get_coordinate_precision(T1)
                t2_precision = get_coordinate_precision(T2)
                
                quality_metrics['precision_changes'].append({
                    'original': p1,
                    'original_precision': original_precision,
                    'new_points': [T1, p1, T2],
                    'new_precisions': [t1_precision, original_precision, t2_precision]
                })
                
                # 座標のシフト量を記録
                shift1 = math.hypot(T1[0] - p1[0], T1[1] - p1[1])
                shift2 = math.hypot(T2[0] - p1[0], T2[1] - p1[1])
                quality_metrics['coordinate_shifts'].extend([shift1, shift2])
                
            else:
                new_coords.append(p1)
        
        print(f"  角丸処理: {corners_in_contour}個")
        print(f"  点数変化: {n} → {len(new_coords)}")
        
        quality_metrics['rounded_points'] += len(new_coords)
        quality_metrics['corners_processed'] += corners_in_contour
    
    # 品質メトリクスの分析
    print(f"\n=== 品質分析結果 ===")
    print(f"総点数変化: {quality_metrics['original_points']} → {quality_metrics['rounded_points']}")
    print(f"点数増加率: {quality_metrics['rounded_points']/quality_metrics['original_points']:.3f}")
    print(f"処理された角: {quality_metrics['corners_processed']}個")
    
    if quality_metrics['precision_changes']:
        print(f"\n精度変化の分析:")
        precision_increases = 0
        max_precision_increase = 0
        
        for change in quality_metrics['precision_changes']:
            orig_prec = change['original_precision']
            new_precs = change['new_precisions']
            max_new_prec = max(new_precs)
            
            if max_new_prec > orig_prec:
                precision_increases += 1
                max_precision_increase = max(max_precision_increase, max_new_prec - orig_prec)
        
        print(f"  精度が増加した角: {precision_increases}個")
        print(f"  最大精度増加: {max_precision_increase}桁")
        
        # 精度変化の例を表示
        print(f"  精度変化の例:")
        for i, change in enumerate(quality_metrics['precision_changes'][:3]):
            orig = change['original']
            new_points = change['new_points']
            print(f"    角{i}: {orig} → {new_points}")
    
    if quality_metrics['coordinate_shifts']:
        shifts = quality_metrics['coordinate_shifts']
        avg_shift = sum(shifts) / len(shifts)
        max_shift = max(shifts)
        print(f"\n座標シフト分析:")
        print(f"  平均シフト距離: {avg_shift:.6f}")
        print(f"  最大シフト距離: {max_shift:.6f}")
    
    return quality_metrics

def convert_pen_to_contours(pen_value):
    """RecordingPenデータを輪郭データに変換"""
    contours = []
    current_coords = []
    current_flags = []
    
    for cmd, pts in pen_value:
        if cmd == "moveTo":
            if current_coords:
                contours.append({'coords': current_coords, 'flags': current_flags})
            current_coords = [pts[0]]
            current_flags = [1]
        elif cmd == "lineTo":
            current_coords.append(pts[0])
            current_flags.append(1)
        elif cmd == "qCurveTo":
            for p in pts[:-1]:
                current_coords.append(p)
                current_flags.append(0)
            current_coords.append(pts[-1])
            current_flags.append(1)
        elif cmd == "curveTo":
            for p in pts[:-1]:
                current_coords.append(p)
                current_flags.append(0)
            current_coords.append(pts[-1])
            current_flags.append(1)
    
    if current_coords:
        contours.append({'coords': current_coords, 'flags': current_flags})
    
    return contours

def get_coordinate_precision(coord):
    """座標の精度（小数点以下桁数）を取得"""
    x, y = coord
    x_precision = 0 if x == int(x) else len(str(x).split('.')[-1])
    y_precision = 0 if y == int(y) else len(str(y).split('.')[-1])
    return max(x_precision, y_precision)

def main():
    """メイン処理"""
    print("OTFフォント専用品質分析")
    print("=" * 50)
    
    # OTFフォントを探す
    otf_info = find_otf_fonts_with_glyphs()
    
    if not otf_info:
        print("❌ 適切なOTFフォントが見つかりませんでした")
        return
    
    print(f"\n✅ OTFテストフォントが見つかりました:")
    print(f"ファイル: {os.path.basename(otf_info['font_path'])}")
    print(f"テストグリフ: {otf_info['glyph_name']}")
    
    # 座標精度分析
    precision_analysis = analyze_cff_coordinate_precision(
        otf_info['pen_data'], 
        otf_info['glyph_name']
    )
    
    if precision_analysis:
        # 角丸処理シミュレート
        quality_metrics = simulate_cff_corner_rounding(otf_info['pen_data'])
        
        if quality_metrics:
            # 問題の特定
            print(f"\n=== 問題の特定 ===")
            
            if precision_analysis['float_ratio'] > 0.5:
                print("⚠️  高い浮動小数点座標比率が検出されました")
                print(f"   浮動小数点座標: {precision_analysis['float_ratio']*100:.1f}%")
                print("   → CFFフォントの高精度座標が原因の可能性")
            
            if quality_metrics['corners_processed'] > 0:
                avg_precision_increase = sum(
                    max(change['new_precisions']) - change['original_precision']
                    for change in quality_metrics['precision_changes']
                ) / len(quality_metrics['precision_changes'])
                
                if avg_precision_increase > 2:
                    print("⚠️  角丸処理で精度が大幅に増加しています")
                    print(f"   平均精度増加: {avg_precision_increase:.1f}桁")
                    print("   → 座標計算での精度劣化の可能性")

if __name__ == "__main__":
    main()