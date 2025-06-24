#!/usr/bin/env python3
"""
角丸処理の各段階を詳細調査
「カクカク」問題がどの段階で発生するかを特定
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

def apply_corner_rounding_detailed(contours, radius):
    """詳細ログ付きの角丸処理"""
    print(f"  角丸処理開始: 半径={radius}")
    
    rounded_contours = []
    
    for contour_idx, contour in enumerate(contours):
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        print(f"    輪郭{contour_idx}: {n}点")
        
        if n < 3:
            rounded_contours.append(contour)
            print(f"      → スキップ（点数不足）")
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
                    
                    # 座標精度の確認
                    print(f"      点{i}: {angle_deg:.1f}度 → 角丸化")
                    print(f"        元座標: {p1}")
                    print(f"        接点T1: {T1}")
                    print(f"        制御点: {p1}")
                    print(f"        接点T2: {T2}")
                    
                    # 3点を追加: T1 (オンカーブ), P1 (制御点), T2 (オンカーブ)
                    new_coords.append(T1)
                    new_flags.append(1)  # オンカーブ
                    new_coords.append(p1)
                    new_flags.append(0)  # オフカーブ（制御点）
                    new_coords.append(T2)
                    new_flags.append(1)  # オンカーブ
                    
                    corners_rounded += 1
                else:
                    new_coords.append(p1)
                    new_flags.append(flags[i])
            else:
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        print(f"      → 完了: {len(new_coords)}点, {corners_rounded}角を角丸化")
        rounded_contours.append({"coords": new_coords, "flags": new_flags})
    
    return rounded_contours

def test_t2charstring_with_proper_setup(pen_value, original_charstring, topDict):
    """適切な設定でT2CharStringPenをテスト"""
    print(f"  T2CharStringPen再構築テスト:")
    
    try:
        # 元のCharStringの属性を取得
        original_width = getattr(original_charstring, 'width', 0)
        original_private = getattr(original_charstring, 'private', None)
        
        print(f"    元のwidth: {original_width}")
        print(f"    元のprivate: {original_private is not None}")
        
        # T2CharStringPenを適切に設定
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
        
        print(f"    新しいCharString作成成功")
        print(f"      width: {getattr(new_charstring, 'width', 'なし')}")
        print(f"      private: {getattr(new_charstring, 'private', 'なし') is not None}")
        
        # 再描画テスト
        verify_pen = RecordingPen()
        new_charstring.draw(verify_pen)
        
        print(f"    再描画成功: {len(verify_pen.value)} コマンド")
        
        # 座標比較
        def extract_coordinates(pen_value):
            coords = []
            for cmd, pts in pen_value:
                if cmd in ["moveTo", "lineTo"]:
                    coords.extend(pts)
                elif cmd in ["qCurveTo", "curveTo"]:
                    coords.extend(pts)
            return coords
        
        original_coords = extract_coordinates(pen_value)
        recreated_coords = extract_coordinates(verify_pen.value)
        
        print(f"    座標数比較: 入力={len(original_coords)}, 出力={len(recreated_coords)}")
        
        if original_coords and recreated_coords:
            # 座標の差分を計算
            min_len = min(len(original_coords), len(recreated_coords))
            max_diff = 0
            total_diff = 0
            
            for i in range(min_len):
                if i < len(original_coords) and i < len(recreated_coords):
                    p1 = original_coords[i]
                    p2 = recreated_coords[i]
                    diff = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                    max_diff = max(max_diff, diff)
                    total_diff += diff
            
            avg_diff = total_diff / min_len if min_len > 0 else 0
            
            print(f"    座標差分: 最大={max_diff:.3f}, 平均={avg_diff:.3f}")
            
            if max_diff > 0.1:
                print(f"    ⚠️ 警告: 座標に差分があります")
                # 差分の大きい点を表示
                for i in range(min(5, min_len)):
                    p1 = original_coords[i]
                    p2 = recreated_coords[i]
                    diff = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                    if diff > 0.01:
                        print(f"      点{i}: {p1} → {p2} (差分: {diff:.3f})")
            else:
                print(f"    ✓ 座標は正確に保持されています")
        
        return new_charstring, True
        
    except Exception as e:
        print(f"    ❌ T2CharStringPen再構築エラー: {e}")
        import traceback
        traceback.print_exc()
        return None, False

def test_corner_rounding_stages():
    """角丸処理の各段階をテスト"""
    
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
    
    print(f"=== 角丸処理段階別テスト ===")
    print(f"テストフォント: {font_file}")
    
    try:
        font = TTFont(font_file)
        
        # CFFテーブル情報
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        # 形状のあるグリフを探す
        available_glyphs = list(charStrings.keys())
        test_glyphs = []
        
        for glyph_name in available_glyphs[:20]:
            try:
                charString = charStrings[glyph_name]
                pen = RecordingPen()
                charString.draw(pen)
                
                if pen.value and len(pen.value) > 5:  # ある程度複雑な形状
                    test_glyphs.append(glyph_name)
                    if len(test_glyphs) >= 2:  # 2個で十分
                        break
            except:
                continue
        
        print(f"テスト対象グリフ: {test_glyphs}")
        
        # 各グリフについて段階別テスト
        for glyph_name in test_glyphs:
            print(f"\n{'='*60}")
            print(f"グリフ '{glyph_name}' の段階別テスト")
            print(f"{'='*60}")
            
            # 段階1: 元のパスデータ取得
            print(f"段階1: 元のパスデータ取得")
            original_charstring = charStrings[glyph_name]
            original_pen = RecordingPen()
            original_charstring.draw(original_pen)
            original_pen_value = original_pen.value
            
            print(f"  ✓ 元のパスコマンド数: {len(original_pen_value)}")
            
            # 段階2: 輪郭データに変換
            print(f"段階2: 輪郭データに変換")
            contours = extract_contours_from_recording_pen(original_pen_value)
            print(f"  ✓ 輪郭数: {len(contours)}")
            
            total_points = sum(len(c['coords']) for c in contours)
            print(f"  ✓ 総点数: {total_points}")
            
            # 段階3: 角丸処理適用
            print(f"段階3: 角丸処理適用")
            rounded_contours = apply_corner_rounding_detailed(contours, radius=15)
            
            rounded_total_points = sum(len(c['coords']) for c in rounded_contours)
            print(f"  ✓ 角丸後総点数: {rounded_total_points}")
            
            # 段階4: RecordingPen形式に変換
            print(f"段階4: RecordingPen形式に変換")
            processed_pen_value = contours_to_recording_pen(rounded_contours)
            print(f"  ✓ 処理後パスコマンド数: {len(processed_pen_value)}")
            
            # 段階5: T2CharStringPenで再構築
            print(f"段階5: T2CharStringPenで再構築")
            new_charstring, success = test_t2charstring_with_proper_setup(
                processed_pen_value, original_charstring, topDict
            )
            
            if success:
                print(f"  ✓ 再構築成功")
                
                # 段階6: 最終検証
                print(f"段階6: 最終検証")
                final_pen = RecordingPen()
                new_charstring.draw(final_pen)
                final_pen_value = final_pen.value
                
                print(f"  ✓ 最終パスコマンド数: {len(final_pen_value)}")
                
                # パスコマンドの詳細比較
                print(f"  パスコマンド比較:")
                print(f"    元: {len(original_pen_value)} コマンド")
                print(f"    処理後: {len(processed_pen_value)} コマンド")
                print(f"    最終: {len(final_pen_value)} コマンド")
                
                # 最初の数コマンドを比較
                print(f"  最初の5コマンド比較:")
                for i in range(min(5, len(original_pen_value), len(final_pen_value))):
                    orig_cmd = original_pen_value[i]
                    final_cmd = final_pen_value[i]
                    print(f"    {i}: 元={orig_cmd} → 最終={final_cmd}")
                
            else:
                print(f"  ❌ 再構築失敗")
        
        print(f"\n{'='*60}")
        print("段階別テスト完了")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_corner_rounding_stages()