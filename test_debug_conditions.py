#!/usr/bin/env python3
"""
角丸処理の条件をデバッグ
なぜグリフが処理されないかを調査
"""

import os
import sys
import math
sys.path.append('.')

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

def extract_contours_from_recording_pen(pen_value):
    """RecordingPenの値から輪郭データを抽出"""
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
        elif cmd == "closePath":
            pass
        elif cmd == "endPath":
            pass
    
    if current_coords:
        contours.append({'coords': current_coords, 'flags': current_flags})
    
    return contours

def analyze_glyph_corners(contours, angle_threshold=75, min_radius=4.0):
    """グリフの角を分析"""
    
    total_corners = 0
    processable_corners = 0
    corner_details = []
    
    for contour_idx, contour in enumerate(contours):
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        if n < 3:
            continue
        
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
            
            total_corners += 1
            
            # 角丸判定
            if angle_deg < angle_threshold and angle_deg > 3:
                max_radius = min(norm1, norm2) / 3.0
                
                if max_radius >= min_radius:
                    processable_corners += 1
                    corner_details.append({
                        'contour': contour_idx,
                        'point': i,
                        'angle': angle_deg,
                        'max_radius': max_radius,
                        'processable': True
                    })
                else:
                    corner_details.append({
                        'contour': contour_idx,
                        'point': i,
                        'angle': angle_deg,
                        'max_radius': max_radius,
                        'processable': False,
                        'reason': f'max_radius({max_radius:.1f}) < min_radius({min_radius})'
                    })
            else:
                corner_details.append({
                    'contour': contour_idx,
                    'point': i,
                    'angle': angle_deg,
                    'max_radius': min(norm1, norm2) / 3.0,
                    'processable': False,
                    'reason': f'angle({angle_deg:.1f}) not in range(3, {angle_threshold})'
                })
    
    return total_corners, processable_corners, corner_details

def test_debug_conditions():
    """角丸処理条件のデバッグ"""
    
    test_fonts = [
        "output_otf_rounded_fixed.otf",
        "output_rounded.otf"
    ]
    
    font_file = None
    for f in test_fonts:
        if os.path.exists(f):
            font_file = f
            break
    
    if not font_file:
        print("エラー: テスト用のOTFフォントファイルが見つかりません")
        return False
    
    print(f"=== 角丸処理条件デバッグ ===")
    print(f"テストフォント: {font_file}")
    
    try:
        font = TTFont(font_file)
        
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        # 複数の条件設定でテスト
        test_conditions = [
            {'name': '厳しい条件', 'angle_threshold': 75, 'min_radius': 4.0},
            {'name': '中程度条件', 'angle_threshold': 120, 'min_radius': 2.0},
            {'name': '緩い条件', 'angle_threshold': 150, 'min_radius': 1.0},
        ]
        
        # テスト対象のグリフを選択
        test_glyphs = []
        for glyph_name in list(charStrings.keys())[:20]:
            try:
                charString = charStrings[glyph_name]
                pen = RecordingPen()
                charString.draw(pen)
                
                if pen.value and len(pen.value) > 5:
                    test_glyphs.append(glyph_name)
                    if len(test_glyphs) >= 5:
                        break
            except:
                continue
        
        print(f"テスト対象グリフ: {test_glyphs}")
        
        for condition in test_conditions:
            print(f"\n{'='*50}")
            print(f"条件: {condition['name']}")
            print(f"角度閾値: {condition['angle_threshold']}度")
            print(f"最小半径: {condition['min_radius']}")
            print(f"{'='*50}")
            
            total_processable = 0
            
            for glyph_name in test_glyphs:
                try:
                    charString = charStrings[glyph_name]
                    pen = RecordingPen()
                    charString.draw(pen)
                    
                    contours = extract_contours_from_recording_pen(pen.value)
                    
                    if not contours:
                        continue
                    
                    total_corners, processable_corners, corner_details = analyze_glyph_corners(
                        contours, condition['angle_threshold'], condition['min_radius']
                    )
                    
                    print(f"\nグリフ '{glyph_name}':")
                    print(f"  総角数: {total_corners}")
                    print(f"  処理可能角数: {processable_corners}")
                    
                    if processable_corners > 0:
                        total_processable += 1
                        print(f"  → このグリフは処理対象")
                        
                        # 処理可能な角の詳細を表示（最初の3つ）
                        processable_details = [d for d in corner_details if d.get('processable', False)]
                        for detail in processable_details[:3]:
                            print(f"    角{detail['point']}: {detail['angle']:.1f}度, 最大半径: {detail['max_radius']:.1f}")
                    else:
                        print(f"  → このグリフは処理対象外")
                        
                        # 処理できない理由を表示（最初の3つ）
                        non_processable_details = [d for d in corner_details if not d.get('processable', True)]
                        for detail in non_processable_details[:3]:
                            print(f"    角{detail['point']}: {detail.get('reason', '不明')}")
                
                except Exception as e:
                    print(f"  エラー: グリフ '{glyph_name}': {e}")
            
            print(f"\n条件 '{condition['name']}' での処理対象グリフ数: {total_processable}/{len(test_glyphs)}")
        
        # 最適な条件を提案
        print(f"\n{'='*60}")
        print("推奨設定:")
        print("- 角度閾値: 120-150度 (より多くの角を処理)")
        print("- 最小半径: 1.0-2.0 (より小さな角も処理)")
        print("- 品質チェック: より緩和")
        print(f"{'='*60}")
        
        return True
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_debug_conditions()