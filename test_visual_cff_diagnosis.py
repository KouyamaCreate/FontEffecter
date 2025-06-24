#!/usr/bin/env python3
"""
CFFフォントの「カクカク」問題の視覚的診断テスト
処理前後のグリフ形状を画像として出力し、問題を特定する
"""

import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import numpy as np

def extract_glyph_paths(font, glyph_name):
    """グリフからパスデータを抽出"""
    if 'CFF ' in font:
        # CFFフォント
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        if glyph_name not in charStrings:
            return None
            
        charString = charStrings[glyph_name]
        pen = RecordingPen()
        charString.draw(pen)
        return pen.value
    else:
        # TrueTypeフォント
        glyf_table = font['glyf']
        if glyph_name not in glyf_table:
            return None
            
        glyph = glyf_table[glyph_name]
        if glyph.isComposite() or not hasattr(glyph, "coordinates"):
            return None
            
        pen = RecordingPen()
        glyph.draw(pen, font['glyf'])
        return pen.value

def recording_pen_to_matplotlib_path(pen_value):
    """RecordingPenの値をmatplotlibのPathに変換"""
    vertices = []
    codes = []
    
    for cmd, pts in pen_value:
        if cmd == "moveTo":
            vertices.append(pts[0])
            codes.append(Path.MOVETO)
        elif cmd == "lineTo":
            vertices.append(pts[0])
            codes.append(Path.LINETO)
        elif cmd == "qCurveTo":
            # 二次ベジェ曲線
            for p in pts[:-1]:
                vertices.append(p)
                codes.append(Path.CURVE3)
            vertices.append(pts[-1])
            codes.append(Path.CURVE3)
        elif cmd == "curveTo":
            # 三次ベジェ曲線
            for p in pts[:-1]:
                vertices.append(p)
                codes.append(Path.CURVE4)
            vertices.append(pts[-1])
            codes.append(Path.CURVE4)
        elif cmd == "closePath":
            if vertices:
                codes.append(Path.CLOSEPOLY)
                vertices.append((0, 0))  # ダミー座標
    
    if not vertices:
        return None
        
    return Path(vertices, codes)

def plot_glyph_comparison(original_path, processed_path, glyph_name, output_file):
    """グリフの処理前後を比較表示"""
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    
    # 元のグリフ
    if original_path:
        patch1 = patches.PathPatch(original_path, facecolor='lightblue', 
                                  edgecolor='blue', alpha=0.7, linewidth=2)
        ax1.add_patch(patch1)
        ax1.set_xlim(original_path.vertices[:, 0].min() - 50, 
                     original_path.vertices[:, 0].max() + 50)
        ax1.set_ylim(original_path.vertices[:, 1].min() - 50, 
                     original_path.vertices[:, 1].max() + 50)
    ax1.set_title(f'Original: {glyph_name}')
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)
    
    # 処理後のグリフ
    if processed_path:
        patch2 = patches.PathPatch(processed_path, facecolor='lightcoral', 
                                  edgecolor='red', alpha=0.7, linewidth=2)
        ax2.add_patch(patch2)
        ax2.set_xlim(processed_path.vertices[:, 0].min() - 50, 
                     processed_path.vertices[:, 0].max() + 50)
        ax2.set_ylim(processed_path.vertices[:, 1].min() - 50, 
                     processed_path.vertices[:, 1].max() + 50)
    ax2.set_title(f'Processed: {glyph_name}')
    ax2.set_aspect('equal')
    ax2.grid(True, alpha=0.3)
    
    # 重ね合わせ
    if original_path and processed_path:
        patch3a = patches.PathPatch(original_path, facecolor='none', 
                                   edgecolor='blue', alpha=0.7, linewidth=2, 
                                   linestyle='--', label='Original')
        patch3b = patches.PathPatch(processed_path, facecolor='none', 
                                   edgecolor='red', alpha=0.7, linewidth=2, 
                                   label='Processed')
        ax3.add_patch(patch3a)
        ax3.add_patch(patch3b)
        
        # 座標範囲を統一
        all_x = np.concatenate([original_path.vertices[:, 0], processed_path.vertices[:, 0]])
        all_y = np.concatenate([original_path.vertices[:, 1], processed_path.vertices[:, 1]])
        ax3.set_xlim(all_x.min() - 50, all_x.max() + 50)
        ax3.set_ylim(all_y.min() - 50, all_y.max() + 50)
        ax3.legend()
    
    ax3.set_title(f'Overlay: {glyph_name}')
    ax3.set_aspect('equal')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"比較画像を保存しました: {output_file}")

def apply_corner_rounding_debug(contours, radius, debug_info):
    """デバッグ情報付きの角丸処理"""
    import math
    
    debug_info['original_contours'] = len(contours)
    debug_info['original_points'] = sum(len(c['coords']) for c in contours)
    
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
                    
                    corners_rounded += 1
                else:
                    new_coords.append(p1)
                    new_flags.append(flags[i])
            else:
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        debug_info[f'contour_{contour_idx}_corners_rounded'] = corners_rounded
        rounded_contours.append({"coords": new_coords, "flags": new_flags})
    
    debug_info['processed_contours'] = len(rounded_contours)
    debug_info['processed_points'] = sum(len(c['coords']) for c in rounded_contours)
    
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
            if flags[i] & 1:  # オンカーブ点
                pen_value.append(("lineTo", (coords[i],)))
            else:  # オフカーブ点（制御点）
                if i + 1 < len(coords) and (flags[i + 1] & 1):
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

def test_cff_visual_diagnosis():
    """CFFフォントの視覚的診断テスト"""
    
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
    
    print(f"テストフォント: {font_file}")
    
    try:
        font = TTFont(font_file)
        
        # フォント形式確認
        if 'CFF ' not in font:
            print("エラー: CFFフォントではありません")
            return
        
        print("CFFフォントを確認しました")
        
        # テスト対象のグリフを選択
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        # 利用可能なグリフから適当なものを選択
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
        
        test_glyphs = test_glyphs[:5]  # 最大5個
        
        print(f"テスト対象グリフ: {test_glyphs}")
        
        # 各グリフについて処理前後を比較
        for glyph_name in test_glyphs:
            print(f"\n=== グリフ '{glyph_name}' の診断 ===")
            
            # 元のパスデータを取得
            original_pen_value = extract_glyph_paths(font, glyph_name)
            if not original_pen_value:
                print(f"グリフ '{glyph_name}' のパスデータが取得できません")
                continue
            
            print(f"元のパスコマンド数: {len(original_pen_value)}")
            
            # 輪郭データに変換
            contours = extract_contours_from_recording_pen(original_pen_value)
            print(f"輪郭数: {len(contours)}")
            for i, c in enumerate(contours):
                print(f"  輪郭{i}: 点数={len(c['coords'])}")
            
            # 角丸処理を適用（デバッグ情報付き）
            debug_info = {}
            rounded_contours = apply_corner_rounding_debug(contours, radius=15, debug_info=debug_info)
            
            print("デバッグ情報:")
            for key, value in debug_info.items():
                print(f"  {key}: {value}")
            
            # 処理後のパスデータに変換
            processed_pen_value = contours_to_recording_pen(rounded_contours)
            print(f"処理後のパスコマンド数: {len(processed_pen_value)}")
            
            # matplotlib Pathに変換
            original_path = recording_pen_to_matplotlib_path(original_pen_value)
            processed_path = recording_pen_to_matplotlib_path(processed_pen_value)
            
            # 比較画像を生成
            output_file = f"visual_diagnosis_{glyph_name}.png"
            plot_glyph_comparison(original_path, processed_path, glyph_name, output_file)
            
            # 座標精度の分析
            if contours:
                coords = contours[0]['coords']
                if coords:
                    print("座標精度分析:")
                    for i, (x, y) in enumerate(coords[:5]):  # 最初の5点
                        print(f"  点{i}: ({x}, {y}) - x整数: {x == int(x)}, y整数: {y == int(y)}")
        
        print(f"\n視覚的診断が完了しました。生成された画像ファイルを確認してください。")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cff_visual_diagnosis()