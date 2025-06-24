#!/usr/bin/env python3
"""
CFFフォントの「カクカク」問題のデバッグ分析
視覚化なしで詳細なデバッグ情報を収集
"""

import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
import math

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
            current_flags = [1]  # オンカーブ
        elif cmd == "lineTo":
            current_coords.append(pts[0])
            current_flags.append(1)  # オンカーブ
        elif cmd == "qCurveTo":
            # 二次ベジェ曲線の制御点とエンドポイント
            for p in pts[:-1]:
                current_coords.append(p)
                current_flags.append(0)  # オフカーブ（制御点）
            current_coords.append(pts[-1])
            current_flags.append(1)  # オンカーブ（エンドポイント）
        elif cmd == "curveTo":
            # 三次ベジェ曲線を二次ベジェに近似
            for p in pts[:-1]:
                current_coords.append(p)
                current_flags.append(0)  # オフカーブ
            current_coords.append(pts[-1])
            current_flags.append(1)  # オンカーブ
        elif cmd == "closePath":
            pass
        elif cmd == "endPath":
            pass
    
    if current_coords:
        contours.append({'coords': current_coords, 'flags': current_flags})
    
    return contours

def analyze_coordinate_precision(coords):
    """座標精度を分析"""
    if not coords:
        return {}
    
    analysis = {
        'total_points': len(coords),
        'integer_x_count': 0,
        'integer_y_count': 0,
        'float_x_count': 0,
        'float_y_count': 0,
        'precision_levels': set(),
        'coordinate_ranges': {
            'x_min': float('inf'),
            'x_max': float('-inf'),
            'y_min': float('inf'),
            'y_max': float('-inf')
        }
    }
    
    for x, y in coords:
        # 整数判定
        if x == int(x):
            analysis['integer_x_count'] += 1
        else:
            analysis['float_x_count'] += 1
        
        if y == int(y):
            analysis['integer_y_count'] += 1
        else:
            analysis['float_y_count'] += 1
        
        # 精度レベル判定
        x_str = str(float(x))
        y_str = str(float(y))
        if '.' in x_str:
            x_precision = len(x_str.split('.')[1])
            analysis['precision_levels'].add(x_precision)
        if '.' in y_str:
            y_precision = len(y_str.split('.')[1])
            analysis['precision_levels'].add(y_precision)
        
        # 座標範囲
        analysis['coordinate_ranges']['x_min'] = min(analysis['coordinate_ranges']['x_min'], x)
        analysis['coordinate_ranges']['x_max'] = max(analysis['coordinate_ranges']['x_max'], x)
        analysis['coordinate_ranges']['y_min'] = min(analysis['coordinate_ranges']['y_min'], y)
        analysis['coordinate_ranges']['y_max'] = max(analysis['coordinate_ranges']['y_max'], y)
    
    return analysis

def apply_corner_rounding_with_debug(contours, radius, debug_info):
    """デバッグ情報付きの角丸処理"""
    
    debug_info['original_contours'] = len(contours)
    debug_info['original_points'] = sum(len(c['coords']) for c in contours)
    debug_info['corner_analysis'] = []
    
    rounded_contours = []
    
    for contour_idx, contour in enumerate(contours):
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        contour_debug = {
            'contour_index': contour_idx,
            'original_points': n,
            'corners_processed': 0,
            'corners_rounded': 0,
            'angles_analyzed': []
        }
        
        if n < 3:
            rounded_contours.append(contour)
            contour_debug['skipped'] = 'too_few_points'
            debug_info['corner_analysis'].append(contour_debug)
            continue
        
        new_coords = []
        new_flags = []
        
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
                new_coords.append(p1)
                new_flags.append(flags[i])
                continue
            
            # 角度計算
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            cos_angle = dot / (norm1 * norm2)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle_deg = math.degrees(math.acos(cos_angle))
            
            angle_info = {
                'point_index': i,
                'angle_degrees': angle_deg,
                'vector_lengths': [norm1, norm2],
                'coordinates': [p0, p1, p2]
            }
            
            contour_debug['corners_processed'] += 1
            
            # 角丸判定
            if angle_deg < 160 and angle_deg > 5:  # 極端な角度を除外
                # 動的半径計算
                max_radius = min(norm1, norm2) / 2.0
                actual_radius = min(radius, max_radius)
                
                if actual_radius > 1.0:  # 最小半径チェック
                    # 角丸処理
                    l1 = min(actual_radius, norm1 * 0.4)
                    l2 = min(actual_radius, norm2 * 0.4)
                    
                    # 接点計算
                    T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
                    T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
                    
                    # 3点を追加: T1 (オンカーブ), P1 (制御点), T2 (オンカーブ)
                    new_coords.append(T1)
                    new_flags.append(1)  # オンカーブ
                    new_coords.append(p1)
                    new_flags.append(0)  # オフカーブ（制御点）
                    new_coords.append(T2)
                    new_flags.append(1)  # オンカーブ
                    
                    contour_debug['corners_rounded'] += 1
                    angle_info['rounded'] = True
                    angle_info['tangent_points'] = [T1, T2]
                    angle_info['control_point'] = p1
                    angle_info['actual_radius'] = actual_radius
                else:
                    new_coords.append(p1)
                    new_flags.append(flags[i])
                    angle_info['rounded'] = False
                    angle_info['skip_reason'] = 'radius_too_small'
            else:
                new_coords.append(p1)
                new_flags.append(flags[i])
                angle_info['rounded'] = False
                angle_info['skip_reason'] = 'angle_threshold'
            
            contour_debug['angles_analyzed'].append(angle_info)
        
        contour_debug['final_points'] = len(new_coords)
        debug_info['corner_analysis'].append(contour_debug)
        rounded_contours.append({"coords": new_coords, "flags": new_flags})
    
    debug_info['processed_contours'] = len(rounded_contours)
    debug_info['processed_points'] = sum(len(c['coords']) for c in rounded_contours)
    
    return rounded_contours

def contours_to_recording_pen(contours):
    """輪郭データをRecordingPenの形式に変換"""
    pen_value = []
    
    for contour in contours:
        coords = contour['coords']
        flags = contour['flags']
        
        if not coords:
            continue
        
        # moveTo
        pen_value.append(("moveTo", (coords[0],)))
        
        i = 1
        while i < len(coords):
            if i >= len(flags):
                break
                
            if flags[i] & 1:  # オンカーブ点
                pen_value.append(("lineTo", (coords[i],)))
            else:  # オフカーブ点（制御点）
                if i + 1 < len(coords) and i + 1 < len(flags) and (flags[i + 1] & 1):
                    # 二次ベジェ曲線
                    pen_value.append(("qCurveTo", (coords[i], coords[i + 1])))
                    i += 1
                else:
                    # 単独の制御点
                    if i + 1 < len(coords):
                        mid_x = (coords[i][0] + coords[i + 1][0]) / 2
                        mid_y = (coords[i][1] + coords[i + 1][1]) / 2
                        pen_value.append(("qCurveTo", (coords[i], (mid_x, mid_y))))
                    else:
                        # 最後の点の場合
                        mid_x = (coords[i][0] + coords[0][0]) / 2
                        mid_y = (coords[i][1] + coords[0][1]) / 2
                        pen_value.append(("qCurveTo", (coords[i], (mid_x, mid_y))))
            i += 1
        
        pen_value.append(("closePath", ()))
    
    return pen_value

def test_t2charstring_reconstruction(original_pen_value, processed_pen_value, glyph_name):
    """T2CharStringPenでの再構築をテスト"""
    print(f"\n=== T2CharStringPen再構築テスト: {glyph_name} ===")
    
    try:
        # T2CharStringPenで再構築
        t2_pen = T2CharStringPen(width=0, glyphSet=None)
        
        for cmd, pts in processed_pen_value:
            if cmd == "moveTo":
                t2_pen.moveTo(pts[0])
            elif cmd == "lineTo":
                t2_pen.lineTo(pts[0])
            elif cmd == "qCurveTo":
                t2_pen.qCurveTo(*pts)
            elif cmd == "curveTo":
                t2_pen.curveTo(*pts)
            elif cmd == "closePath":
                t2_pen.closePath()
        
        # CharStringを取得
        charstring = t2_pen.getCharString()
        
        # 再描画してパスデータを確認
        reconstructed_pen = RecordingPen()
        charstring.draw(reconstructed_pen)
        
        print(f"元のパスコマンド数: {len(original_pen_value)}")
        print(f"処理後のパスコマンド数: {len(processed_pen_value)}")
        print(f"再構築後のパスコマンド数: {len(reconstructed_pen.value)}")
        
        # コマンドの詳細比較
        print("\n元のパスコマンド:")
        for i, (cmd, pts) in enumerate(original_pen_value[:10]):  # 最初の10個
            print(f"  {i}: {cmd} {pts}")
        
        print("\n処理後のパスコマンド:")
        for i, (cmd, pts) in enumerate(processed_pen_value[:10]):
            print(f"  {i}: {cmd} {pts}")
        
        print("\n再構築後のパスコマンド:")
        for i, (cmd, pts) in enumerate(reconstructed_pen.value[:10]):
            print(f"  {i}: {cmd} {pts}")
        
        # 座標の精度比較
        def extract_coordinates(pen_value):
            coords = []
            for cmd, pts in pen_value:
                if cmd in ["moveTo", "lineTo"]:
                    coords.extend(pts)
                elif cmd in ["qCurveTo", "curveTo"]:
                    coords.extend(pts)
            return coords
        
        original_coords = extract_coordinates(original_pen_value)
        processed_coords = extract_coordinates(processed_pen_value)
        reconstructed_coords = extract_coordinates(reconstructed_pen.value)
        
        print(f"\n座標数比較:")
        print(f"  元: {len(original_coords)}")
        print(f"  処理後: {len(processed_coords)}")
        print(f"  再構築後: {len(reconstructed_coords)}")
        
        if processed_coords and reconstructed_coords:
            # 座標の差分を計算
            min_len = min(len(processed_coords), len(reconstructed_coords))
            max_diff = 0
            for i in range(min_len):
                if i < len(processed_coords) and i < len(reconstructed_coords):
                    p1 = processed_coords[i]
                    p2 = reconstructed_coords[i]
                    diff = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                    max_diff = max(max_diff, diff)
            
            print(f"  最大座標差分: {max_diff}")
            
            if max_diff > 1.0:
                print("  ⚠️ 警告: T2CharStringPen再構築で座標が大きく変化しています")
                return False
            else:
                print("  ✓ T2CharStringPen再構築は正常です")
                return True
        
    except Exception as e:
        print(f"  ❌ T2CharStringPen再構築エラー: {e}")
        return False

def test_cff_debug_analysis():
    """CFFフォントのデバッグ分析メイン"""
    
    # テスト用のOTFフォントファイルを探す
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
        return
    
    print(f"=== CFFフォント「カクカク」問題デバッグ分析 ===")
    print(f"テストフォント: {font_file}")
    
    try:
        font = TTFont(font_file)
        
        # フォント形式確認
        if 'CFF ' not in font:
            print("エラー: CFFフォントではありません")
            return
        
        print("✓ CFFフォントを確認しました")
        
        # CFFテーブル情報
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        print(f"✓ グリフ数: {len(charStrings)}")
        
        # テスト対象のグリフを選択
        available_glyphs = list(charStrings.keys())
        test_glyphs = []
        
        # 一般的なグリフ名を優先
        priority_glyphs = ['A', 'B', 'O', 'a', 'o', 'e', 'n', 'H', 'M']
        for g in priority_glyphs:
            if g in available_glyphs:
                test_glyphs.append(g)
        
        # 足りない場合は他のグリフも追加
        for g in available_glyphs[:10]:
            if g not in test_glyphs and g != '.notdef':
                test_glyphs.append(g)
        
        test_glyphs = test_glyphs[:3]  # 最大3個に制限
        
        print(f"✓ テスト対象グリフ: {test_glyphs}")
        
        # 各グリフについて詳細分析
        for glyph_name in test_glyphs:
            print(f"\n{'='*60}")
            print(f"グリフ '{glyph_name}' の詳細分析")
            print(f"{'='*60}")
            
            # 元のパスデータを取得
            charString = charStrings[glyph_name]
            original_pen = RecordingPen()
            charString.draw(original_pen)
            original_pen_value = original_pen.value
            
            if not original_pen_value:
                print(f"グリフ '{glyph_name}' のパスデータが空です")
                continue
            
            print(f"✓ 元のパスコマンド数: {len(original_pen_value)}")
            
            # 輪郭データに変換
            contours = extract_contours_from_recording_pen(original_pen_value)
            print(f"✓ 輪郭数: {len(contours)}")
            
            for i, contour in enumerate(contours):
                coords = contour['coords']
                flags = contour['flags']
                print(f"  輪郭{i}: 点数={len(coords)}, フラグ数={len(flags)}")
                
                # 座標精度分析
                coord_analysis = analyze_coordinate_precision(coords)
                print(f"    座標精度分析:")
                print(f"      総点数: {coord_analysis['total_points']}")
                print(f"      整数X座標: {coord_analysis['integer_x_count']}")
                print(f"      浮動小数点X座標: {coord_analysis['float_x_count']}")
                print(f"      整数Y座標: {coord_analysis['integer_y_count']}")
                print(f"      浮動小数点Y座標: {coord_analysis['float_y_count']}")
                print(f"      精度レベル: {sorted(coord_analysis['precision_levels'])}")
                
                # 最初の数点の座標を表示
                print(f"    最初の5点の座標:")
                for j, ((x, y), flag) in enumerate(zip(coords[:5], flags[:5])):
                    on_curve = "オンカーブ" if flag & 1 else "オフカーブ"
                    print(f"      点{j}: ({x}, {y}) - {on_curve}")
            
            # 角丸処理を適用（デバッグ情報付き）
            print(f"\n--- 角丸処理分析 ---")
            debug_info = {}
            rounded_contours = apply_corner_rounding_with_debug(contours, radius=15, debug_info=debug_info)
            
            print(f"処理結果:")
            print(f"  元の輪郭数: {debug_info['original_contours']}")
            print(f"  元の総点数: {debug_info['original_points']}")
            print(f"  処理後の輪郭数: {debug_info['processed_contours']}")
            print(f"  処理後の総点数: {debug_info['processed_points']}")
            
            # 各輪郭の角丸処理詳細
            for contour_analysis in debug_info['corner_analysis']:
                idx = contour_analysis['contour_index']
                print(f"  輪郭{idx}:")
                print(f"    元の点数: {contour_analysis['original_points']}")
                print(f"    最終点数: {contour_analysis['final_points']}")
                print(f"    処理した角: {contour_analysis['corners_processed']}")
                print(f"    角丸化した角: {contour_analysis['corners_rounded']}")
                
                # 角度分析の詳細（最初の3つのみ）
                for angle_info in contour_analysis['angles_analyzed'][:3]:
                    print(f"      点{angle_info['point_index']}: {angle_info['angle_degrees']:.1f}度", end="")
                    if angle_info.get('rounded'):
                        print(f" → 角丸化 (半径: {angle_info['actual_radius']:.1f})")
                    else:
                        print(f" → スキップ ({angle_info.get('skip_reason', 'unknown')})")
            
            # 処理後のパスデータに変換
            processed_pen_value = contours_to_recording_pen(rounded_contours)
            print(f"✓ 処理後のパスコマンド数: {len(processed_pen_value)}")
            
            # T2CharStringPen再構築テスト
            reconstruction_success = test_t2charstring_reconstruction(
                original_pen_value, processed_pen_value, glyph_name
            )
            
            if not reconstruction_success:
                print(f"❌ グリフ '{glyph_name}': T2CharStringPen再構築で問題が発生")
            else:
                print(f"✓ グリフ '{glyph_name}': T2CharStringPen再構築は正常")
        
        print(f"\n{'='*60}")
        print("デバッグ分析完了")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cff_debug_analysis()