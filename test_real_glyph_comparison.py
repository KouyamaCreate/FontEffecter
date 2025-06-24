#!/usr/bin/env python3
"""
実際の形状を持つグリフでOTF/TTF比較テストを実行
"""

import sys
import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

def find_fonts_with_actual_glyphs():
    """実際の形状を持つグリフがあるフォントを探す"""
    print("実際の形状を持つグリフがあるフォントを探しています...")
    
    # より一般的なフォントパスを探す
    font_paths = [
        "/System/Library/Fonts/",
        "/Library/Fonts/",
        "/System/Library/Fonts/Helvetica.ttc",  # 直接指定
        "/System/Library/Fonts/Times.ttc",      # 直接指定
    ]
    
    suitable_fonts = []
    
    for path in font_paths:
        try:
            if os.path.exists(path):
                if os.path.isfile(path):
                    # 単一ファイル
                    suitable_fonts.append(path)
                else:
                    # ディレクトリ
                    for file in os.listdir(path):
                        if file.lower().endswith(('.otf', '.ttf')):
                            full_path = os.path.join(path, file)
                            suitable_fonts.append(full_path)
        except (OSError, PermissionError):
            continue
    
    print(f"発見されたフォントファイル: {len(suitable_fonts)}個")
    
    # 各フォントで実際の形状を持つグリフを探す
    for font_path in suitable_fonts[:10]:  # 最初の10個をチェック
        try:
            result = analyze_font_for_shaped_glyphs(font_path)
            if result:
                return result
        except Exception as e:
            print(f"フォント分析エラー: {os.path.basename(font_path)} - {e}")
            continue
    
    return None

def analyze_font_for_shaped_glyphs(font_path):
    """フォント内の形状を持つグリフを分析"""
    try:
        font = TTFont(font_path)
        
        has_glyf = 'glyf' in font
        has_cff = 'CFF ' in font
        
        print(f"\n分析中: {os.path.basename(font_path)}")
        print(f"  glyf: {'あり' if has_glyf else 'なし'}")
        print(f"  CFF: {'あり' if has_cff else 'なし'}")
        
        if has_cff:
            # CFFフォントの場合
            cff_table = font['CFF ']
            cff = cff_table.cff
            topDict = cff.topDictIndex[0]
            charStrings = topDict.CharStrings
            
            # 実際の形状を持つグリフを探す
            test_glyphs = ['A', 'B', 'C', 'a', 'b', 'c', 'zero', 'one', 'two']
            for glyph_name in test_glyphs:
                if glyph_name in charStrings:
                    charString = charStrings[glyph_name]
                    pen = RecordingPen()
                    charString.draw(pen)
                    
                    if len(pen.value) > 0:
                        # 実際のパスデータがある
                        print(f"  ✅ 形状あり: {glyph_name} ({len(pen.value)}コマンド)")
                        return {
                            'font_path': font_path,
                            'font_type': 'CFF',
                            'glyph_name': glyph_name,
                            'font': font
                        }
        
        elif has_glyf:
            # TTFフォントの場合
            glyf_table = font['glyf']
            
            test_glyphs = ['A', 'B', 'C', 'a', 'b', 'c', 'zero', 'one', 'two']
            for glyph_name in test_glyphs:
                if glyph_name in glyf_table:
                    glyph = glyf_table[glyph_name]
                    
                    if (not glyph.isComposite() and 
                        hasattr(glyph, "coordinates") and 
                        glyph.coordinates and 
                        glyph.numberOfContours > 0):
                        
                        print(f"  ✅ 形状あり: {glyph_name} ({len(glyph.coordinates)}点)")
                        return {
                            'font_path': font_path,
                            'font_type': 'TTF',
                            'glyph_name': glyph_name,
                            'font': font
                        }
        
        print(f"  ❌ 適切なグリフが見つかりません")
        return None
        
    except Exception as e:
        print(f"  エラー: {e}")
        return None

def detailed_cff_analysis(font, glyph_name):
    """CFFグリフの詳細分析"""
    print(f"\n=== CFFグリフ詳細分析: {glyph_name} ===")
    
    try:
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        charString = charStrings[glyph_name]
        
        # RecordingPenでパスを記録
        pen = RecordingPen()
        charString.draw(pen)
        
        print(f"パスコマンド数: {len(pen.value)}")
        
        # 各コマンドを詳細分析
        all_coords = []
        for i, (cmd, pts) in enumerate(pen.value):
            print(f"  [{i}] {cmd}: {pts}")
            
            if cmd in ['moveTo', 'lineTo']:
                all_coords.extend(pts)
            elif cmd in ['qCurveTo', 'curveTo']:
                all_coords.extend(pts)
        
        if all_coords:
            print(f"\n座標分析:")
            print(f"  総座標数: {len(all_coords)}")
            
            # 座標精度の分析
            float_coords = 0
            int_coords = 0
            precision_samples = []
            
            for coord in all_coords:
                x, y = coord
                if x != int(x) or y != int(y):
                    float_coords += 1
                    precision_samples.append(coord)
                else:
                    int_coords += 1
            
            print(f"  整数座標: {int_coords}個")
            print(f"  浮動小数点座標: {float_coords}個")
            
            if precision_samples:
                print(f"  浮動小数点座標の例:")
                for coord in precision_samples[:5]:
                    print(f"    {coord}")
            
            # 座標範囲
            x_coords = [coord[0] for coord in all_coords]
            y_coords = [coord[1] for coord in all_coords]
            print(f"  X範囲: {min(x_coords):.3f} ～ {max(x_coords):.3f}")
            print(f"  Y範囲: {min(y_coords):.3f} ～ {max(y_coords):.3f}")
        
        return pen.value
        
    except Exception as e:
        print(f"CFF分析エラー: {e}")
        return None

def detailed_ttf_analysis(font, glyph_name):
    """TTFグリフの詳細分析"""
    print(f"\n=== TTFグリフ詳細分析: {glyph_name} ===")
    
    try:
        glyf_table = font['glyf']
        glyph = glyf_table[glyph_name]
        
        coords = list(glyph.coordinates)
        flags = list(glyph.flags)
        endPts = list(glyph.endPtsOfContours)
        
        print(f"座標数: {len(coords)}")
        print(f"輪郭数: {len(endPts)}")
        print(f"輪郭終点: {endPts}")
        
        # 座標の詳細分析
        print(f"\n座標分析:")
        for i, coord in enumerate(coords[:10]):
            flag = flags[i] if i < len(flags) else 0
            on_curve = "オンカーブ" if flag & 1 else "オフカーブ"
            print(f"  [{i}] {coord} ({on_curve})")
        
        if len(coords) > 10:
            print(f"  ... (残り{len(coords)-10}点)")
        
        # 座標精度の分析（TTFは通常整数だが確認）
        float_coords = 0
        for coord in coords:
            x, y = coord
            if x != int(x) or y != int(y):
                float_coords += 1
        
        print(f"浮動小数点座標: {float_coords}個")
        
        # 座標範囲
        x_coords = [coord[0] for coord in coords]
        y_coords = [coord[1] for coord in coords]
        print(f"X範囲: {min(x_coords)} ～ {max(x_coords)}")
        print(f"Y範囲: {min(y_coords)} ～ {max(y_coords)}")
        
        return {
            'coords': coords,
            'flags': flags,
            'endPts': endPts
        }
        
    except Exception as e:
        print(f"TTF分析エラー: {e}")
        return None

def simulate_corner_rounding_with_precision_tracking(data, font_type, radius=10):
    """角丸処理をシミュレートし、精度の変化を追跡"""
    print(f"\n=== 角丸処理シミュレート ({font_type}, radius={radius}) ===")
    
    if font_type == 'CFF':
        # CFFデータ（RecordingPenの結果）を処理
        contours = convert_recording_to_contours(data)
    else:
        # TTFデータを処理
        contours = convert_ttf_to_contours(data)
    
    if not contours:
        print("輪郭データがありません")
        return
    
    print(f"処理前輪郭数: {len(contours)}")
    
    total_original_points = 0
    total_rounded_points = 0
    precision_changes = []
    
    for i, contour in enumerate(contours):
        coords = contour['coords']
        n = len(coords)
        total_original_points += n
        
        print(f"\n輪郭{i}: {n}点")
        
        # 簡単な角丸処理
        new_coords = []
        corners_processed = 0
        
        for j in range(n):
            if n < 3:
                new_coords.append(coords[j])
                continue
            
            p0 = coords[j - 1]
            p1 = coords[j]
            p2 = coords[(j + 1) % n]
            
            # 角度計算
            v1 = (p0[0] - p1[0], p0[1] - p1[1])
            v2 = (p2[0] - p1[0], p2[1] - p1[1])
            norm1 = math.hypot(*v1)
            norm2 = math.hypot(*v2)
            
            if norm1 == 0 or norm2 == 0:
                new_coords.append(p1)
                continue
            
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            cos_angle = dot / (norm1 * norm2)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle_deg = math.degrees(math.acos(cos_angle))
            
            # 角丸判定（140度未満）
            if angle_deg < 140:
                # 角丸処理: 3点に置き換え
                l1 = min(radius, norm1 * 0.5)
                l2 = min(radius, norm2 * 0.5)
                
                T1 = (p1[0] + (p0[0] - p1[0]) * l1 / norm1, 
                      p1[1] + (p0[1] - p1[1]) * l1 / norm1)
                T2 = (p1[0] + (p2[0] - p1[0]) * l2 / norm2, 
                      p1[1] + (p2[1] - p1[1]) * l2 / norm2)
                
                new_coords.extend([T1, p1, T2])
                corners_processed += 1
                
                # 精度変化を記録
                precision_changes.append({
                    'original': p1,
                    'new': [T1, p1, T2]
                })
            else:
                new_coords.append(p1)
        
        total_rounded_points += len(new_coords)
        print(f"  角丸処理: {corners_processed}個")
        print(f"  点数変化: {n} → {len(new_coords)}")
    
    print(f"\n全体の点数変化: {total_original_points} → {total_rounded_points}")
    print(f"変化率: {total_rounded_points/total_original_points:.3f}")
    
    # 精度変化の分析
    if precision_changes:
        print(f"\n精度変化の分析:")
        print(f"角丸処理された角: {len(precision_changes)}個")
        
        for i, change in enumerate(precision_changes[:3]):  # 最初の3個を表示
            orig = change['original']
            new_points = change['new']
            print(f"  角{i}: {orig} → {new_points}")

def convert_recording_to_contours(pen_value):
    """RecordingPenの記録を輪郭データに変換"""
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

def convert_ttf_to_contours(ttf_data):
    """TTFデータを輪郭データに変換"""
    coords = ttf_data['coords']
    flags = ttf_data['flags']
    endPts = ttf_data['endPts']
    
    contours = []
    start_idx = 0
    
    for end_idx in endPts:
        contour_coords = coords[start_idx:end_idx + 1]
        contour_flags = flags[start_idx:end_idx + 1]
        
        contours.append({
            'coords': contour_coords,
            'flags': contour_flags
        })
        
        start_idx = end_idx + 1
    
    return contours

def main():
    """メイン処理"""
    print("実グリフ形状でのOTF/TTF品質比較テスト")
    print("=" * 60)
    
    # 実際の形状を持つフォントを探す
    font_info = find_fonts_with_actual_glyphs()
    
    if not font_info:
        print("❌ 適切なテストフォントが見つかりませんでした")
        return
    
    print(f"\n✅ テストフォントが見つかりました:")
    print(f"ファイル: {os.path.basename(font_info['font_path'])}")
    print(f"形式: {font_info['font_type']}")
    print(f"テストグリフ: {font_info['glyph_name']}")
    
    # 詳細分析実行
    if font_info['font_type'] == 'CFF':
        cff_data = detailed_cff_analysis(font_info['font'], font_info['glyph_name'])
        if cff_data:
            simulate_corner_rounding_with_precision_tracking(cff_data, 'CFF')
    else:
        ttf_data = detailed_ttf_analysis(font_info['font'], font_info['glyph_name'])
        if ttf_data:
            simulate_corner_rounding_with_precision_tracking(ttf_data, 'TTF')

if __name__ == "__main__":
    main()