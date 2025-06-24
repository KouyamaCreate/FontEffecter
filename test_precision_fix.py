#!/usr/bin/env python3
"""
T2CharStringPenの座標精度問題を解決するテスト
高精度座標を保持する修正版を実装
"""

import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.misc.psCharStrings import T2CharString

class HighPrecisionT2CharStringPen(T2CharStringPen):
    """高精度座標を保持するT2CharStringPen"""
    
    def __init__(self, width, glyphSet, precision=1000):
        super().__init__(width, glyphSet)
        self.precision = precision  # 座標精度倍率
        self._original_commands = []  # 元のコマンドを保存
    
    def _roundPoint(self, pt):
        """座標の丸め処理をオーバーライド - 高精度を保持"""
        # 元の実装では整数に丸められるが、高精度を保持
        x, y = pt
        # 精度倍率を適用して小数点以下を保持
        return (round(x * self.precision) / self.precision, 
                round(y * self.precision) / self.precision)
    
    def moveTo(self, pt):
        """moveTo - 高精度座標で記録"""
        self._original_commands.append(('moveTo', pt))
        super().moveTo(self._roundPoint(pt))
    
    def lineTo(self, pt):
        """lineTo - 高精度座標で記録"""
        self._original_commands.append(('lineTo', pt))
        super().lineTo(self._roundPoint(pt))
    
    def qCurveTo(self, *points):
        """qCurveTo - 高精度座標で記録"""
        self._original_commands.append(('qCurveTo', points))
        rounded_points = [self._roundPoint(pt) for pt in points]
        super().qCurveTo(*rounded_points)
    
    def curveTo(self, *points):
        """curveTo - 高精度座標で記録"""
        self._original_commands.append(('curveTo', points))
        rounded_points = [self._roundPoint(pt) for pt in points]
        super().curveTo(*rounded_points)

def create_optimized_charstring(pen_value, original_charstring, topDict, use_high_precision=True):
    """最適化されたCharString作成"""
    
    # 元のCharStringの属性を取得
    original_width = getattr(original_charstring, 'width', 0)
    original_private = getattr(original_charstring, 'private', None)
    
    if use_high_precision:
        # 高精度T2CharStringPenを使用
        t2_pen = HighPrecisionT2CharStringPen(width=original_width, glyphSet=None, precision=100)
    else:
        # 標準T2CharStringPenを使用
        t2_pen = T2CharStringPen(width=original_width, glyphSet=None)
    
    # パスコマンドを描画
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
    
    # CharStringを取得
    new_charstring = t2_pen.getCharString()
    
    # 属性を適切に設定
    new_charstring.width = original_width
    
    # PrivateDictを設定
    if original_private is not None:
        new_charstring.private = original_private
    elif hasattr(topDict, 'Private') and topDict.Private:
        new_charstring.private = topDict.Private
    
    return new_charstring

def apply_corner_rounding_optimized(contours, radius):
    """最適化された角丸処理 - 座標精度を考慮"""
    
    rounded_contours = []
    
    for contour in contours:
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        if n < 3:
            rounded_contours.append(contour)
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
            
            # 角丸判定
            if angle_deg < 160 and angle_deg > 5:
                # 動的半径計算
                max_radius = min(norm1, norm2) / 2.0
                actual_radius = min(radius, max_radius)
                
                if actual_radius > 1.0:
                    # 高精度角丸処理
                    l1 = min(actual_radius, norm1 * 0.4)
                    l2 = min(actual_radius, norm2 * 0.4)
                    
                    # 接点計算（高精度保持）
                    T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
                    T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
                    
                    # 制御点の最適化（より滑らかな曲線のため）
                    control_factor = 0.552  # 円に近いベジェ曲線の係数
                    ctrl_x = p1[0] + (T1[0] - p1[0] + T2[0] - p1[0]) * control_factor * 0.5
                    ctrl_y = p1[1] + (T1[1] - p1[1] + T2[1] - p1[1]) * control_factor * 0.5
                    optimized_control = (ctrl_x, ctrl_y)
                    
                    # 3点を追加: T1 (オンカーブ), 最適化制御点 (オフカーブ), T2 (オンカーブ)
                    new_coords.append(T1)
                    new_flags.append(1)  # オンカーブ
                    new_coords.append(optimized_control)
                    new_flags.append(0)  # オフカーブ（制御点）
                    new_coords.append(T2)
                    new_flags.append(1)  # オンカーブ
                else:
                    new_coords.append(p1)
                    new_flags.append(flags[i])
            else:
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        rounded_contours.append({"coords": new_coords, "flags": new_flags})
    
    return rounded_contours

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

def test_precision_fix():
    """座標精度修正のテスト"""
    
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
    
    print(f"=== 座標精度修正テスト ===")
    print(f"テストフォント: {font_file}")
    
    try:
        font = TTFont(font_file)
        
        # CFFテーブル情報
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
                
                if pen.value and len(pen.value) > 10:  # 複雑な形状
                    test_glyph = glyph_name
                    break
            except:
                continue
        
        if not test_glyph:
            print("適切なテストグリフが見つかりません")
            return
        
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
        
        # 最適化された角丸処理を適用
        print(f"\n=== 最適化された角丸処理 ===")
        rounded_contours = apply_corner_rounding_optimized(contours, radius=15)
        
        total_points = sum(len(c['coords']) for c in contours)
        rounded_total_points = sum(len(c['coords']) for c in rounded_contours)
        print(f"点数変化: {total_points} → {rounded_total_points}")
        
        # RecordingPen形式に変換
        processed_pen_value = contours_to_recording_pen(rounded_contours)
        print(f"処理後パスコマンド数: {len(processed_pen_value)}")
        
        # 標準T2CharStringPenでテスト
        print(f"\n=== 標準T2CharStringPenテスト ===")
        standard_charstring = create_optimized_charstring(
            processed_pen_value, original_charstring, topDict, use_high_precision=False
        )
        
        standard_pen = RecordingPen()
        standard_charstring.draw(standard_pen)
        
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
        
        std_max_diff, std_avg_diff = calculate_coordinate_difference(processed_pen_value, standard_pen.value)
        print(f"標準版 - 最大差分: {std_max_diff:.3f}, 平均差分: {std_avg_diff:.3f}")
        
        # 高精度T2CharStringPenでテスト
        print(f"\n=== 高精度T2CharStringPenテスト ===")
        precision_charstring = create_optimized_charstring(
            processed_pen_value, original_charstring, topDict, use_high_precision=True
        )
        
        precision_pen = RecordingPen()
        precision_charstring.draw(precision_pen)
        
        prec_max_diff, prec_avg_diff = calculate_coordinate_difference(processed_pen_value, precision_pen.value)
        print(f"高精度版 - 最大差分: {prec_max_diff:.3f}, 平均差分: {prec_avg_diff:.3f}")
        
        # 改善度を計算
        improvement_max = ((std_max_diff - prec_max_diff) / std_max_diff * 100) if std_max_diff > 0 else 0
        improvement_avg = ((std_avg_diff - prec_avg_diff) / std_avg_diff * 100) if std_avg_diff > 0 else 0
        
        print(f"\n=== 改善結果 ===")
        print(f"最大差分改善: {improvement_max:.1f}%")
        print(f"平均差分改善: {improvement_avg:.1f}%")
        
        if prec_max_diff < std_max_diff * 0.5:
            print("✓ 大幅な精度改善が確認されました！")
            
            # 実際にフォントに適用してテスト
            print(f"\n=== フォント適用テスト ===")
            charStrings[test_glyph] = precision_charstring
            
            # 新しいフォントファイルとして保存
            output_file = "output_precision_fixed.otf"
            font.save(output_file)
            print(f"精度修正版フォントを保存: {output_file}")
            
            # 保存されたフォントを検証
            test_font = TTFont(output_file)
            test_cff = test_font['CFF '].cff.topDictIndex[0].CharStrings
            test_charstring = test_cff[test_glyph]
            
            verify_pen = RecordingPen()
            test_charstring.draw(verify_pen)
            
            verify_max_diff, verify_avg_diff = calculate_coordinate_difference(processed_pen_value, verify_pen.value)
            print(f"保存後検証 - 最大差分: {verify_max_diff:.3f}, 平均差分: {verify_avg_diff:.3f}")
            
            if verify_max_diff < 1.0:
                print("✓ フォント保存後も高精度が維持されています！")
                return True
            else:
                print("⚠️ フォント保存後に精度が低下しました")
                return False
        else:
            print("❌ 期待した精度改善が得られませんでした")
            return False
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_precision_fix()
    if success:
        print("\n🎉 座標精度修正が成功しました！")
    else:
        print("\n❌ 座標精度修正に失敗しました")