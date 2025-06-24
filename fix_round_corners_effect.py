#!/usr/bin/env python3
"""
角丸効果の最終修正版
T2CharStringの座標変化を前提とした最適化実装
"""

import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

def apply_optimized_cff_corner_rounding(font, radius=10, quality_level='medium'):
    """
    CFFフォント用の最適化された角丸処理
    T2CharStringの座標変化を考慮した実装
    """
    print("CFFフォント最適化角丸処理を開始します...")
    
    try:
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
    except Exception as cff_error:
        print(f"エラー: CFFテーブルの読み込みに失敗しました: {cff_error}")
        return font
    
    processed_count = 0
    
    # 品質レベルに応じた設定
    if quality_level == 'high':
        angle_threshold = 120  # より多くの角を処理
        min_radius = 3.0
        radius_factor = 0.8
    elif quality_level == 'low':
        angle_threshold = 60   # 鋭角のみ処理
        min_radius = 8.0
        radius_factor = 0.4
    else:  # medium
        angle_threshold = 90
        min_radius = 5.0
        radius_factor = 0.6
    
    for glyph_name in charStrings.keys():
        try:
            # CFFグリフからパスデータを取得
            charString = charStrings[glyph_name]
            
            # RecordingPenを使ってパスデータを記録
            pen = RecordingPen()
            charString.draw(pen)
            
            if not pen.value:
                continue
            
            # 輪郭データを抽出
            contours = extract_contours_from_recording_pen(pen.value)
            
            if not contours:
                continue
            
            # 最適化された角丸処理を適用
            rounded_contours = apply_cff_optimized_rounding(
                contours, radius, angle_threshold, min_radius, radius_factor
            )
            
            # 変化があった場合のみ更新
            if has_significant_changes(contours, rounded_contours):
                # 新しいCharStringを作成
                new_charstring = create_optimized_charstring(
                    rounded_contours, charString, topDict
                )
                
                if new_charstring:
                    charStrings[glyph_name] = new_charstring
                    processed_count += 1
                    print(f"  グリフ '{glyph_name}' の処理完了")
            
        except Exception as e:
            print(f"  エラー: グリフ '{glyph_name}' の処理中に例外が発生: {str(e)}")
    
    print(f"CFFフォントの最適化角丸処理が完了しました。処理されたグリフ数: {processed_count}個")
    return font

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

def apply_cff_optimized_rounding(contours, radius, angle_threshold, min_radius, radius_factor):
    """CFF最適化角丸処理"""
    
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
            if angle_deg < angle_threshold and angle_deg > 5:
                max_radius = min(norm1, norm2) / 3.0
                actual_radius = min(radius * radius_factor, max_radius)
                
                if actual_radius >= min_radius:
                    # T2CharStringの特性を考慮した角丸処理
                    result = create_cff_compatible_corner(
                        p0, p1, p2, actual_radius, norm1, norm2, angle_deg
                    )
                    
                    if result:
                        new_coords.extend(result['coords'])
                        new_flags.extend(result['flags'])
                    else:
                        new_coords.append(p1)
                        new_flags.append(flags[i])
                else:
                    new_coords.append(p1)
                    new_flags.append(flags[i])
            else:
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        rounded_contours.append({"coords": new_coords, "flags": new_flags})
    
    return rounded_contours

def create_cff_compatible_corner(p0, p1, p2, radius, norm1, norm2, angle_deg):
    """CFF互換の角丸コーナーを作成"""
    
    v1 = (p0[0] - p1[0], p0[1] - p1[1])
    v2 = (p2[0] - p1[0], p2[1] - p1[1])
    
    # 角度に応じて処理方法を選択
    if angle_deg < 30:
        # 非常に鋭角 - 単純な面取り
        l1 = min(radius * 0.3, norm1 * 0.15)
        l2 = min(radius * 0.3, norm2 * 0.15)
        
        T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
        T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
        
        return {
            'coords': [T1, T2],
            'flags': [1, 1]  # 直線接続
        }
    
    elif angle_deg < 60:
        # 鋭角 - 控えめなベジェ曲線
        l1 = min(radius * 0.4, norm1 * 0.2)
        l2 = min(radius * 0.4, norm2 * 0.2)
        
        T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
        T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
        
        # 制御点を保守的に設定
        ctrl_factor = 0.3
        ctrl_x = p1[0] + (T1[0] - p1[0] + T2[0] - p1[0]) * ctrl_factor * 0.5
        ctrl_y = p1[1] + (T1[1] - p1[1] + T2[1] - p1[1]) * ctrl_factor * 0.5
        
        return {
            'coords': [T1, (ctrl_x, ctrl_y), T2],
            'flags': [1, 0, 1]  # ベジェ曲線
        }
    
    else:
        # 中程度の角 - 標準的なベジェ曲線
        l1 = min(radius * 0.5, norm1 * 0.25)
        l2 = min(radius * 0.5, norm2 * 0.25)
        
        T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
        T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
        
        # より滑らかな制御点
        ctrl_factor = 0.5
        ctrl_x = p1[0] + (T1[0] - p1[0] + T2[0] - p1[0]) * ctrl_factor * 0.5
        ctrl_y = p1[1] + (T1[1] - p1[1] + T2[1] - p1[1]) * ctrl_factor * 0.5
        
        return {
            'coords': [T1, (ctrl_x, ctrl_y), T2],
            'flags': [1, 0, 1]  # ベジェ曲線
        }

def has_significant_changes(original_contours, rounded_contours):
    """有意な変化があるかチェック"""
    original_points = sum(len(c['coords']) for c in original_contours)
    rounded_points = sum(len(c['coords']) for c in rounded_contours)
    
    # 点数が20%以上変化した場合は有意な変化とみなす
    return abs(rounded_points - original_points) / original_points > 0.2

def create_optimized_charstring(contours, original_charstring, topDict):
    """最適化されたCharStringを作成"""
    
    # 輪郭データをRecordingPen形式に変換
    pen_value = contours_to_recording_pen(contours)
    
    # 元のCharStringの属性を取得
    original_width = getattr(original_charstring, 'width', 0)
    original_private = getattr(original_charstring, 'private', None)
    
    try:
        # T2CharStringPenで新しいCharStringを作成
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
        
        # PrivateDictを設定
        if original_private is not None:
            new_charstring.private = original_private
        elif hasattr(topDict, 'Private') and topDict.Private:
            new_charstring.private = topDict.Private
        
        return new_charstring
        
    except Exception as e:
        print(f"    CharString作成エラー: {e}")
        return None

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
                    pen_value.append(("lineTo", (coords[i],)))
            i += 1
        
        pen_value.append(("closePath", ()))
    
    return pen_value

def test_optimized_fix():
    """最適化修正のテスト"""
    
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
    
    print(f"=== 最適化角丸修正テスト ===")
    print(f"テストフォント: {font_file}")
    
    try:
        font = TTFont(font_file)
        
        # 最適化された角丸処理を適用
        optimized_font = apply_optimized_cff_corner_rounding(
            font, radius=12, quality_level='medium'
        )
        
        # 新しいフォントファイルとして保存
        output_file = "output_optimized_rounded.otf"
        optimized_font.save(output_file)
        print(f"最適化角丸フォントを保存: {output_file}")
        
        # 保存されたフォントを検証
        test_font = TTFont(output_file)
        if 'CFF ' in test_font:
            print("✓ 最適化角丸フォントが正常に保存されました")
            return True
        else:
            print("❌ フォント保存に問題があります")
            return False
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_optimized_fix()
    if success:
        print("\n🎉 最適化角丸修正が成功しました！")
        print("output_optimized_rounded.otf ファイルを確認してください。")
    else:
        print("\n❌ 最適化角丸修正に失敗しました")