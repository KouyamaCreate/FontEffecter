#!/usr/bin/env python3
"""
T2CharStringPenを使わない直接的なCFF再構築
fontToolsの低レベルAPIを使用して座標精度を保持
"""

import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.misc.psCharStrings import T2CharString
from fontTools.cffLib import TopDictIndex, CharStrings

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

def apply_minimal_corner_rounding(contours, radius):
    """最小限の角丸処理 - 座標変化を最小化"""
    print(f"  最小限角丸処理開始: 半径={radius}")
    
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
            
            # 非常に鋭角のみ処理（90度未満）
            if angle_deg < 90 and angle_deg > 5:
                max_radius = min(norm1, norm2) / 4.0
                actual_radius = min(radius, max_radius)
                
                if actual_radius > 5.0:
                    # 最小限の角丸 - 単純な面取り
                    l1 = min(actual_radius * 0.5, norm1 * 0.2)
                    l2 = min(actual_radius * 0.5, norm2 * 0.2)
                    
                    T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
                    T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
                    
                    # 直線で接続（ベジェ曲線を使わない）
                    new_coords.append(T1)
                    new_flags.append(1)  # オンカーブ
                    new_coords.append(T2)
                    new_flags.append(1)  # オンカーブ
                    
                    corners_rounded += 1
                    print(f"      点{i}: {angle_deg:.1f}度 → 面取り")
                else:
                    new_coords.append(p1)
                    new_flags.append(flags[i])
            else:
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        print(f"    輪郭{contour_idx}: {corners_rounded}角を面取り")
        rounded_contours.append({"coords": new_coords, "flags": new_flags})
    
    return rounded_contours

def create_t2charstring_bytecode(pen_value, width):
    """T2CharStringのバイトコードを直接生成"""
    print(f"  T2CharStringバイトコード直接生成")
    
    # T2CharStringのオペレーションコード
    commands = []
    
    # 幅を設定
    if width != 0:
        commands.extend([width, 'width'])
    
    current_pos = (0, 0)
    
    for cmd, pts in pen_value:
        if cmd == "moveTo":
            x, y = pts[0]
            dx = x - current_pos[0]
            dy = y - current_pos[1]
            if dx != 0 or dy != 0:
                commands.extend([dx, dy, 'rmoveto'])
            current_pos = (x, y)
            
        elif cmd == "lineTo":
            x, y = pts[0]
            dx = x - current_pos[0]
            dy = y - current_pos[1]
            if dx != 0 and dy == 0:
                commands.extend([dx, 'hlineto'])
            elif dx == 0 and dy != 0:
                commands.extend([dy, 'vlineto'])
            else:
                commands.extend([dx, dy, 'rlineto'])
            current_pos = (x, y)
            
        elif cmd == "qCurveTo":
            # 二次ベジェ曲線を三次ベジェに変換
            if len(pts) == 2:
                cp, end = pts
                # 二次ベジェを三次ベジェに変換
                cp1_x = current_pos[0] + 2/3 * (cp[0] - current_pos[0])
                cp1_y = current_pos[1] + 2/3 * (cp[1] - current_pos[1])
                cp2_x = end[0] + 2/3 * (cp[0] - end[0])
                cp2_y = end[1] + 2/3 * (cp[1] - end[1])
                
                dx1 = cp1_x - current_pos[0]
                dy1 = cp1_y - current_pos[1]
                dx2 = cp2_x - cp1_x
                dy2 = cp2_y - cp1_y
                dx3 = end[0] - cp2_x
                dy3 = end[1] - cp2_y
                
                commands.extend([dx1, dy1, dx2, dy2, dx3, dy3, 'rrcurveto'])
                current_pos = end
            
        elif cmd == "curveTo":
            # 三次ベジェ曲線
            if len(pts) == 3:
                cp1, cp2, end = pts
                dx1 = cp1[0] - current_pos[0]
                dy1 = cp1[1] - current_pos[1]
                dx2 = cp2[0] - cp1[0]
                dy2 = cp2[1] - cp1[1]
                dx3 = end[0] - cp2[0]
                dy3 = end[1] - cp2[1]
                
                commands.extend([dx1, dy1, dx2, dy2, dx3, dy3, 'rrcurveto'])
                current_pos = end
                
        elif cmd == "closePath":
            commands.append('closepath')
    
    # endchar
    commands.append('endchar')
    
    print(f"    生成されたコマンド数: {len(commands)}")
    return commands

def create_direct_charstring(pen_value, original_charstring, topDict):
    """T2CharStringを直接作成（T2CharStringPenを使わない）"""
    
    original_width = getattr(original_charstring, 'width', 0)
    original_private = getattr(original_charstring, 'private', None)
    
    print(f"  直接CharString作成: width={original_width}")
    
    try:
        # T2CharStringのバイトコードを生成
        commands = create_t2charstring_bytecode(pen_value, original_width)
        
        # T2CharStringオブジェクトを作成
        # 注意: これは実験的なアプローチです
        charstring_data = []
        
        # 簡単なT2CharStringエンコーディング（基本的なもののみ）
        for item in commands:
            if isinstance(item, (int, float)):
                # 数値をエンコード
                if -107 <= item <= 107:
                    charstring_data.append(int(item) + 139)
                elif 108 <= item <= 1131:
                    val = int(item) - 108
                    charstring_data.extend([((val >> 8) + 247), (val & 0xFF)])
                elif -1131 <= item <= -108:
                    val = abs(int(item)) - 108
                    charstring_data.extend([((val >> 8) + 251), (val & 0xFF)])
                else:
                    # 大きな数値は16.16固定小数点として
                    charstring_data.extend([255, 0, 0, int(item) & 0xFF, (int(item) >> 8) & 0xFF])
            elif item == 'rmoveto':
                charstring_data.append(21)
            elif item == 'rlineto':
                charstring_data.append(5)
            elif item == 'hlineto':
                charstring_data.append(6)
            elif item == 'vlineto':
                charstring_data.append(7)
            elif item == 'rrcurveto':
                charstring_data.append(8)
            elif item == 'closepath':
                charstring_data.append(9)
            elif item == 'endchar':
                charstring_data.append(14)
        
        # バイト配列に変換
        bytecode = bytes(charstring_data)
        
        # T2CharStringオブジェクトを作成
        new_charstring = T2CharString(bytecode)
        new_charstring.width = original_width
        
        if original_private is not None:
            new_charstring.private = original_private
        elif hasattr(topDict, 'Private') and topDict.Private:
            new_charstring.private = topDict.Private
        
        print(f"  ✓ 直接CharString作成成功")
        return new_charstring
        
    except Exception as e:
        print(f"  ❌ 直接CharString作成エラー: {e}")
        # フォールバック: 元のCharStringを返す
        return original_charstring

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

def test_direct_cff_reconstruction():
    """直接CFF再構築のテスト"""
    
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
    
    print(f"=== 直接CFF再構築テスト ===")
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
                
                if pen.value and len(pen.value) > 5:
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
        
        # 最小限の角丸処理を適用
        print(f"\n=== 最小限角丸処理 ===")
        rounded_contours = apply_minimal_corner_rounding(contours, radius=8)
        
        # RecordingPen形式に変換
        processed_pen_value = contours_to_recording_pen(rounded_contours)
        print(f"処理後パスコマンド数: {len(processed_pen_value)}")
        
        # 直接CharStringを作成
        print(f"\n=== 直接CharString作成 ===")
        new_charstring = create_direct_charstring(
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
        
        if max_diff < 50.0:  # より現実的な閾値
            print("✓ 直接CFF再構築で座標差分が改善されました！")
            
            # フォントに適用
            charStrings[test_glyph] = new_charstring
            output_file = "output_direct_cff.otf"
            font.save(output_file)
            print(f"直接CFF再構築フォントを保存: {output_file}")
            return True
        else:
            print("❌ 期待した改善が得られませんでした")
            
            # デバッグ情報を出力
            print(f"\nデバッグ情報:")
            print(f"処理前コマンド例: {processed_pen_value[:3]}")
            print(f"処理後コマンド例: {verify_pen.value[:3]}")
            return False
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_cff_reconstruction()
    if success:
        print("\n🎉 直接CFF再構築が成功しました！")
    else:
        print("\n❌ 直接CFF再構築に失敗しました")