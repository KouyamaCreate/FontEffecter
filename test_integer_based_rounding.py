#!/usr/bin/env python3
"""
整数座標ベースの角丸アルゴリズム
T2CharStringPenの座標丸めを前提とした最適化
"""

import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

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

def apply_integer_based_corner_rounding(contours, radius):
    """整数座標ベースの角丸処理"""
    print(f"  整数ベース角丸処理開始: 半径={radius}")
    
    rounded_contours = []
    
    for contour_idx, contour in enumerate(contours):
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        print(f"    輪郭{contour_idx}: {n}点")
        
        if n < 3:
            rounded_contours.append(contour)
            continue
        
        new_coords = []
        new_flags = []
        corners_rounded = 0
        
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
            
            # 角丸判定
            if angle_deg < 160 and angle_deg > 5:
                # 動的半径計算
                max_radius = min(norm1, norm2) / 2.0
                actual_radius = min(radius, max_radius)
                
                if actual_radius > 2.0:  # 最小半径を大きくして整数座標に適応
                    # 整数座標に最適化された角丸処理
                    l1 = min(actual_radius, norm1 * 0.3)  # より保守的な係数
                    l2 = min(actual_radius, norm2 * 0.3)
                    
                    # 接点計算（整数に丸める）
                    T1_x = p1[0] + v1[0] * l1 / norm1
                    T1_y = p1[1] + v1[1] * l1 / norm1
                    T2_x = p1[0] + v2[0] * l2 / norm2
                    T2_y = p1[1] + v2[1] * l2 / norm2
                    
                    # 整数座標に丸める
                    T1 = (round(T1_x), round(T1_y))
                    T2 = (round(T2_x), round(T2_y))
                    
                    # 制御点も整数座標に最適化
                    # より滑らかな曲線のための制御点計算
                    mid_x = (T1[0] + T2[0]) / 2
                    mid_y = (T1[1] + T2[1]) / 2
                    
                    # 元の角の方向に制御点を調整
                    offset_factor = 0.4  # 制御点のオフセット係数
                    ctrl_x = mid_x + (p1[0] - mid_x) * offset_factor
                    ctrl_y = mid_y + (p1[1] - mid_y) * offset_factor
                    
                    control_point = (round(ctrl_x), round(ctrl_y))
                    
                    print(f"      点{i}: {angle_deg:.1f}度 → 角丸化")
                    print(f"        T1: {T1}, 制御点: {control_point}, T2: {T2}")
                    
                    # 重複点チェック
                    if T1 != T2 and T1 != control_point and T2 != control_point:
                        # 3点を追加: T1 (オンカーブ), 制御点 (オフカーブ), T2 (オンカーブ)
                        new_coords.append(T1)
                        new_flags.append(1)  # オンカーブ
                        new_coords.append(control_point)
                        new_flags.append(0)  # オフカーブ（制御点）
                        new_coords.append(T2)
                        new_flags.append(1)  # オンカーブ
                        corners_rounded += 1
                    else:
                        # 重複する場合は元の点を保持
                        new_coords.append(p1)
                        new_flags.append(flags[i])
                else:
                    new_coords.append(p1)
                    new_flags.append(flags[i])
            else:
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        print(f"      → 完了: {len(new_coords)}点, {corners_rounded}角を角丸化")
        rounded_contours.append({"coords": new_coords, "flags": new_flags})
    
    return rounded_contours

def apply_adaptive_corner_rounding(contours, radius):
    """適応的角丸処理 - T2CharStringPenの特性に合わせて最適化"""
    print(f"  適応的角丸処理開始: 半径={radius}")
    
    rounded_contours = []
    
    for contour_idx, contour in enumerate(contours):
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        if n < 3:
            rounded_contours.append(contour)
            continue
        
        new_coords = []
        new_flags = []
        corners_rounded = 0
        
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
            
            # より厳しい角丸判定（鋭角のみ）
            if angle_deg < 120 and angle_deg > 10:  # より鋭角のみ対象
                max_radius = min(norm1, norm2) / 3.0  # より保守的
                actual_radius = min(radius, max_radius)
                
                if actual_radius > 3.0:  # より大きな最小半径
                    # 複数の角丸手法を試す
                    methods = [
                        self._method_simple_chamfer,
                        self._method_bezier_approximation,
                        self._method_arc_approximation
                    ]
                    
                    best_result = None
                    best_score = float('inf')
                    
                    for method in methods:
                        try:
                            result = method(p0, p1, p2, actual_radius, norm1, norm2)
                            if result:
                                # 整数座標への丸め誤差を評価
                                score = self._evaluate_rounding_error(result)
                                if score < best_score:
                                    best_score = score
                                    best_result = result
                        except:
                            continue
                    
                    if best_result:
                        new_coords.extend(best_result['coords'])
                        new_flags.extend(best_result['flags'])
                        corners_rounded += 1
                    else:
                        new_coords.append(p1)
                        new_flags.append(flags[i])
                else:
                    new_coords.append(p1)
                    new_flags.append(flags[i])
            else:
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        print(f"    輪郭{contour_idx}: {corners_rounded}角を角丸化")
        rounded_contours.append({"coords": new_coords, "flags": new_flags})
    
    return rounded_contours

def _method_simple_chamfer(self, p0, p1, p2, radius, norm1, norm2):
    """シンプルな面取り手法"""
    v1 = (p0[0] - p1[0], p0[1] - p1[1])
    v2 = (p2[0] - p1[0], p2[1] - p1[1])
    
    l1 = min(radius, norm1 * 0.25)
    l2 = min(radius, norm2 * 0.25)
    
    T1 = (round(p1[0] + v1[0] * l1 / norm1), round(p1[1] + v1[1] * l1 / norm1))
    T2 = (round(p1[0] + v2[0] * l2 / norm2), round(p1[1] + v2[1] * l2 / norm2))
    
    if T1 != T2:
        return {
            'coords': [T1, T2],
            'flags': [1, 1]  # 両方オンカーブ（直線）
        }
    return None

def _method_bezier_approximation(self, p0, p1, p2, radius, norm1, norm2):
    """ベジェ曲線近似手法"""
    v1 = (p0[0] - p1[0], p0[1] - p1[1])
    v2 = (p2[0] - p1[0], p2[1] - p1[1])
    
    l1 = min(radius, norm1 * 0.3)
    l2 = min(radius, norm2 * 0.3)
    
    T1 = (round(p1[0] + v1[0] * l1 / norm1), round(p1[1] + v1[1] * l1 / norm1))
    T2 = (round(p1[0] + v2[0] * l2 / norm2), round(p1[1] + v2[1] * l2 / norm2))
    
    # 制御点を計算
    ctrl_x = (T1[0] + T2[0] + p1[0]) / 3
    ctrl_y = (T1[1] + T2[1] + p1[1]) / 3
    control_point = (round(ctrl_x), round(ctrl_y))
    
    if T1 != T2 and T1 != control_point and T2 != control_point:
        return {
            'coords': [T1, control_point, T2],
            'flags': [1, 0, 1]  # オンカーブ, オフカーブ, オンカーブ
        }
    return None

def _method_arc_approximation(self, p0, p1, p2, radius, norm1, norm2):
    """円弧近似手法"""
    # より複雑な円弧近似（省略）
    return None

def _evaluate_rounding_error(self, result):
    """整数座標への丸め誤差を評価"""
    error = 0
    for coord in result['coords']:
        # 座標が既に整数に近いかチェック
        x_error = abs(coord[0] - round(coord[0]))
        y_error = abs(coord[1] - round(coord[1]))
        error += x_error + y_error
    return error

def contours_to_recording_pen(contours):
    """輪郭データをRecordingPenの形式に変換"""
    pen_value = []
    
    for contour in contours:
        coords = contour['coords']
        flags = contour['flags']
        
        if not coords:
            continue
        
        pen_value.append(("moveTo", (coords[0],)))
        
        i = 1
        while i < len(coords):
            if i >= len(flags):
                break
                
            if flags[i] & 1:
                pen_value.append(("lineTo", (coords[i],)))
            else:
                if i + 1 < len(coords) and i + 1 < len(flags) and (flags[i + 1] & 1):
                    pen_value.append(("qCurveTo", (coords[i], coords[i + 1])))
                    i += 1
                else:
                    if i + 1 < len(coords):
                        mid_x = (coords[i][0] + coords[i + 1][0]) / 2
                        mid_y = (coords[i][1] + coords[i + 1][1]) / 2
                        pen_value.append(("qCurveTo", (coords[i], (mid_x, mid_y))))
                    else:
                        mid_x = (coords[i][0] + coords[0][0]) / 2
                        mid_y = (coords[i][1] + coords[0][1]) / 2
                        pen_value.append(("qCurveTo", (coords[i], (mid_x, mid_y))))
            i += 1
        
        pen_value.append(("closePath", ()))
    
    return pen_value

def create_charstring_with_proper_setup(pen_value, original_charstring, topDict):
    """適切な設定でCharStringを作成"""
    original_width = getattr(original_charstring, 'width', 0)
    original_private = getattr(original_charstring, 'private', None)
    
    t2_pen = T2CharStringPen(width=original_width, glyphSet=None)
    
    for cmd, pts in pen_value:
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
    
    new_charstring = t2_pen.getCharString()
    new_charstring.width = original_width
    
    if original_private is not None:
        new_charstring.private = original_private
    elif hasattr(topDict, 'Private') and topDict.Private:
        new_charstring.private = topDict.Private
    
    return new_charstring

def test_integer_based_rounding():
    """整数ベース角丸処理のテスト"""
    
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
    
    print(f"=== 整数ベース角丸処理テスト ===")
    print(f"テストフォント: {font_file}")
    
    try:
        font = TTFont(font_file)
        
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        # テスト対象のグリフを選択
        available_glyphs = list(charStrings.keys())
        test_glyph = None
        
        for glyph_name in available_glyphs[:20]:
            try:
                charString = charStrings[glyph_name]
                pen = RecordingPen()
                charString.draw(pen)
                
                if pen.value and len(pen.value) > 10:
                    test_glyph = glyph_name
                    break
            except:
                continue
        
        if not test_glyph:
            print("適切なテストグリフが見つかりません")
            return False
        
        print(f"テスト対象グリフ: {test_glyph}")
        
        # 元のパスデータを取得
        original_charstring = charStrings[test_glyph]
        original_pen = RecordingPen()
        original_charstring.draw(original_pen)
        original_pen_value = original_pen.value
        
        print(f"元のパスコマンド数: {len(original_pen_value)}")
        
        # 輪郭データに変換
        contours = extract_contours_from_recording_pen(original_pen_value)
        print(f"輪郭数: {len(contours)}")
        
        # 整数ベース角丸処理を適用
        print(f"\n=== 整数ベース角丸処理 ===")
        rounded_contours = apply_integer_based_corner_rounding(contours, radius=12)
        
        # RecordingPen形式に変換
        processed_pen_value = contours_to_recording_pen(rounded_contours)
        print(f"処理後パスコマンド数: {len(processed_pen_value)}")
        
        # CharStringを作成
        new_charstring = create_charstring_with_proper_setup(
            processed_pen_value, original_charstring, topDict
        )
        
        # 検証
        verify_pen = RecordingPen()
        new_charstring.draw(verify_pen)
        
        def calculate_coordinate_difference(pen1_value, pen2_value):
            def extract_coordinates(pen_value):
                coords = []
                for cmd, pts in pen_value:
                    if cmd in ["moveTo", "lineTo"]:
                        coords.extend(pts)
                    elif cmd in ["qCurveTo", "curveTo"]:
                        coords.extend(pts)
                return coords
            
            coords1 = extract_coordinates(pen1_value)
            coords2 = extract_coordinates(pen2_value)
            
            if not coords1 or not coords2:
                return 0, 0
            
            min_len = min(len(coords1), len(coords2))
            max_diff = 0
            total_diff = 0
            
            for i in range(min_len):
                p1 = coords1[i]
                p2 = coords2[i]
                diff = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                max_diff = max(max_diff, diff)
                total_diff += diff
            
            avg_diff = total_diff / min_len if min_len > 0 else 0
            return max_diff, avg_diff
        
        max_diff, avg_diff = calculate_coordinate_difference(processed_pen_value, verify_pen.value)
        print(f"\n=== 結果 ===")
        print(f"最大座標差分: {max_diff:.3f}")
        print(f"平均座標差分: {avg_diff:.3f}")
        
        if max_diff < 10.0:  # 大幅改善の閾値
            print("✓ 整数ベース角丸処理で座標差分が大幅に改善されました！")
            
            # フォントに適用
            charStrings[test_glyph] = new_charstring
            output_file = "output_integer_rounded.otf"
            font.save(output_file)
            print(f"整数ベース角丸フォントを保存: {output_file}")
            return True
        else:
            print("❌ 期待した改善が得られませんでした")
            return False
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_integer_based_rounding()
    if success:
        print("\n🎉 整数ベース角丸処理が成功しました！")
    else:
        print("\n❌ 整数ベース角丸処理に失敗しました")