#!/usr/bin/env python3
"""
OTFフォントの角丸処理品質診断スクリプト

OTFとTTFフォントで同じグリフを処理し、各段階での品質変化を詳細に追跡する。
座標精度、パス取得方法、角丸処理の品質を比較分析する。
"""

import sys
import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

def analyze_font_format(font_path):
    """フォント形式を詳細分析"""
    print(f"\n=== フォント形式分析: {os.path.basename(font_path)} ===")
    
    try:
        font = TTFont(font_path)
        
        has_glyf = 'glyf' in font
        has_cff = 'CFF ' in font
        
        print(f"glyf テーブル: {'あり' if has_glyf else 'なし'}")
        print(f"CFF テーブル: {'あり' if has_cff else 'なし'}")
        
        if has_cff:
            print("フォント形式: OpenType/CFF (.otf)")
            cff_table = font['CFF ']
            cff = cff_table.cff
            topDict = cff.topDictIndex[0]
            charStrings = topDict.CharStrings
            print(f"グリフ数: {len(charStrings)}")
            
            # CFF特有の情報
            if hasattr(topDict, 'Private') and topDict.Private:
                private = topDict.Private
                print(f"PrivateDict: あり")
                if hasattr(private, 'nominalWidthX'):
                    print(f"  nominalWidthX: {private.nominalWidthX}")
                if hasattr(private, 'defaultWidthX'):
                    print(f"  defaultWidthX: {private.defaultWidthX}")
            
        elif has_glyf:
            print("フォント形式: TrueType (.ttf)")
            glyf_table = font['glyf']
            print(f"グリフ数: {len(glyf_table)}")
        
        return font, has_cff, has_glyf
        
    except Exception as e:
        print(f"エラー: フォント読み込み失敗: {e}")
        return None, False, False

def extract_glyph_paths_cff(font, glyph_name):
    """CFFフォントからグリフパスを抽出（詳細ログ付き）"""
    print(f"\n--- CFFグリフパス抽出: {glyph_name} ---")
    
    try:
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        if glyph_name not in charStrings:
            print(f"グリフ '{glyph_name}' が見つかりません")
            return None
        
        charString = charStrings[glyph_name]
        print(f"CharString取得成功")
        
        # RecordingPenでパスを記録
        pen = RecordingPen()
        charString.draw(pen)
        
        print(f"RecordingPen記録完了")
        print(f"記録されたコマンド数: {len(pen.value)}")
        
        # コマンドの詳細を表示
        for i, (cmd, pts) in enumerate(pen.value):
            if i < 10:  # 最初の10コマンドのみ表示
                print(f"  [{i}] {cmd}: {pts}")
            elif i == 10:
                print(f"  ... (残り{len(pen.value)-10}コマンド)")
                break
        
        # 座標の精度分析
        all_coords = []
        for cmd, pts in pen.value:
            if cmd in ['moveTo', 'lineTo']:
                all_coords.extend(pts)
            elif cmd in ['qCurveTo', 'curveTo']:
                all_coords.extend(pts)
        
        if all_coords:
            print(f"総座標数: {len(all_coords)}")
            
            # 座標精度の分析
            float_coords = []
            int_coords = []
            
            for coord in all_coords:
                x, y = coord
                if x != int(x) or y != int(y):
                    float_coords.append(coord)
                else:
                    int_coords.append(coord)
            
            print(f"整数座標: {len(int_coords)}個")
            print(f"浮動小数点座標: {len(float_coords)}個")
            
            if float_coords:
                print("浮動小数点座標の例:")
                for i, coord in enumerate(float_coords[:5]):
                    print(f"  {coord}")
                    if i >= 4:
                        break
        
        return pen.value
        
    except Exception as e:
        print(f"CFFパス抽出エラー: {e}")
        return None

def extract_glyph_paths_ttf(font, glyph_name):
    """TTFフォントからグリフパスを抽出（詳細ログ付き）"""
    print(f"\n--- TTFグリフパス抽出: {glyph_name} ---")
    
    try:
        glyf_table = font['glyf']
        
        if glyph_name not in glyf_table:
            print(f"グリフ '{glyph_name}' が見つかりません")
            return None
        
        glyph = glyf_table[glyph_name]
        
        if glyph.isComposite():
            print("コンポジットグリフです")
            return None
        
        if not hasattr(glyph, "coordinates") or glyph.numberOfContours == 0:
            print("座標データがありません")
            return None
        
        coords = list(glyph.coordinates)
        flags = list(glyph.flags)
        endPts = list(glyph.endPtsOfContours)
        
        print(f"座標数: {len(coords)}")
        print(f"輪郭数: {len(endPts)}")
        
        # 座標の詳細分析
        print("座標の例:")
        for i, coord in enumerate(coords[:10]):
            flag = flags[i] if i < len(flags) else 0
            on_curve = "オンカーブ" if flag & 1 else "オフカーブ"
            print(f"  [{i}] {coord} ({on_curve})")
            if i >= 9:
                break
        
        # 座標精度の分析（TTFは通常整数）
        float_coords = []
        for coord in coords:
            x, y = coord
            if x != int(x) or y != int(y):
                float_coords.append(coord)
        
        print(f"浮動小数点座標: {len(float_coords)}個")
        if float_coords:
            print("浮動小数点座標の例:")
            for coord in float_coords[:5]:
                print(f"  {coord}")
        
        return {
            'coords': coords,
            'flags': flags,
            'endPts': endPts
        }
        
    except Exception as e:
        print(f"TTFパス抽出エラー: {e}")
        return None

def convert_recording_to_contours(pen_value):
    """RecordingPenの記録を輪郭データに変換"""
    print(f"\n--- RecordingPen → 輪郭データ変換 ---")
    
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
            # 制御点を追加
            for p in pts[:-1]:
                current_coords.append(p)
                current_flags.append(0)  # オフカーブ
            # 終点を追加
            current_coords.append(pts[-1])
            current_flags.append(1)  # オンカーブ
        elif cmd == "curveTo":
            # 三次ベジェ曲線を二次ベジェ曲線に近似
            for p in pts[:-1]:
                current_coords.append(p)
                current_flags.append(0)  # オフカーブ
            current_coords.append(pts[-1])
            current_flags.append(1)  # オンカーブ
        elif cmd in ["closePath", "endPath"]:
            pass
    
    if current_coords:
        contours.append({'coords': current_coords, 'flags': current_flags})
    
    print(f"変換結果: {len(contours)}個の輪郭")
    for i, contour in enumerate(contours):
        print(f"  輪郭{i}: {len(contour['coords'])}点")
        
        # 座標精度の確認
        float_count = 0
        for coord in contour['coords']:
            x, y = coord
            if x != int(x) or y != int(y):
                float_count += 1
        
        print(f"    浮動小数点座標: {float_count}個")
    
    return contours

def simulate_corner_rounding(contours, radius=10):
    """角丸処理をシミュレート（品質追跡付き）"""
    print(f"\n--- 角丸処理シミュレート (radius={radius}) ---")
    
    if not contours:
        return contours
    
    total_original_points = sum(len(c['coords']) for c in contours)
    print(f"処理前総点数: {total_original_points}")
    
    # 簡単な角丸処理（実際の処理を簡略化）
    rounded_contours = []
    
    for i, contour in enumerate(contours):
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        if n < 3:
            rounded_contours.append(contour)
            continue
        
        print(f"  輪郭{i}: {n}点を処理中...")
        
        new_coords = []
        new_flags = []
        
        # 各点で角度を計算し、角丸が必要かを判定
        corners_rounded = 0
        
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
                new_flags.append(flags[j])
                continue
            
            # 角度計算
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            cos_angle = dot / (norm1 * norm2)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle_deg = math.degrees(math.acos(cos_angle))
            
            # 角丸判定（140度未満で角丸）
            if angle_deg < 140:
                # 角丸処理: 3点に置き換え
                l1 = min(radius, norm1 * 0.5)
                l2 = min(radius, norm2 * 0.5)
                
                T1 = (p1[0] + (p0[0] - p1[0]) * l1 / norm1, 
                      p1[1] + (p0[1] - p1[1]) * l1 / norm1)
                T2 = (p1[0] + (p2[0] - p1[0]) * l2 / norm2, 
                      p1[1] + (p2[1] - p1[1]) * l2 / norm2)
                
                new_coords.extend([T1, p1, T2])
                new_flags.extend([1, 0, 1])  # オンカーブ, オフカーブ, オンカーブ
                corners_rounded += 1
            else:
                new_coords.append(p1)
                new_flags.append(flags[j])
        
        print(f"    角丸処理: {corners_rounded}個の角を処理")
        print(f"    点数変化: {n} → {len(new_coords)}")
        
        rounded_contours.append({
            'coords': new_coords,
            'flags': new_flags
        })
    
    total_new_points = sum(len(c['coords']) for c in rounded_contours)
    print(f"処理後総点数: {total_new_points}")
    print(f"点数変化率: {total_new_points/total_original_points:.2f}")
    
    return rounded_contours

def analyze_coordinate_precision(contours, label=""):
    """座標精度を詳細分析"""
    print(f"\n--- 座標精度分析 {label} ---")
    
    if not contours:
        print("輪郭データがありません")
        return
    
    all_coords = []
    for contour in contours:
        all_coords.extend(contour['coords'])
    
    if not all_coords:
        print("座標データがありません")
        return
    
    # 精度分析
    integer_coords = 0
    float_coords = 0
    precision_levels = {}
    
    for coord in all_coords:
        x, y = coord
        
        if x == int(x) and y == int(y):
            integer_coords += 1
        else:
            float_coords += 1
            
            # 小数点以下の桁数を計算
            x_precision = len(str(x).split('.')[-1]) if '.' in str(x) else 0
            y_precision = len(str(y).split('.')[-1]) if '.' in str(y) else 0
            max_precision = max(x_precision, y_precision)
            
            precision_levels[max_precision] = precision_levels.get(max_precision, 0) + 1
    
    print(f"総座標数: {len(all_coords)}")
    print(f"整数座標: {integer_coords}個 ({integer_coords/len(all_coords)*100:.1f}%)")
    print(f"浮動小数点座標: {float_coords}個 ({float_coords/len(all_coords)*100:.1f}%)")
    
    if precision_levels:
        print("小数点精度分布:")
        for precision, count in sorted(precision_levels.items()):
            print(f"  {precision}桁: {count}個")
    
    # 座標範囲の分析
    x_coords = [coord[0] for coord in all_coords]
    y_coords = [coord[1] for coord in all_coords]
    
    print(f"X座標範囲: {min(x_coords):.3f} ～ {max(x_coords):.3f}")
    print(f"Y座標範囲: {min(y_coords):.3f} ～ {max(y_coords):.3f}")

def compare_font_processing(otf_path, ttf_path, glyph_name='A'):
    """OTFとTTFフォントの処理を比較"""
    print(f"\n{'='*60}")
    print(f"フォント処理比較: グリフ '{glyph_name}'")
    print(f"{'='*60}")
    
    # OTFフォント処理
    print(f"\n🔍 OTFフォント処理")
    otf_font, otf_is_cff, _ = analyze_font_format(otf_path)
    if otf_font and otf_is_cff:
        otf_paths = extract_glyph_paths_cff(otf_font, glyph_name)
        if otf_paths:
            otf_contours = convert_recording_to_contours(otf_paths)
            analyze_coordinate_precision(otf_contours, "(OTF原始)")
            otf_rounded = simulate_corner_rounding(otf_contours)
            analyze_coordinate_precision(otf_rounded, "(OTF角丸後)")
    
    # TTFフォント処理
    print(f"\n🔍 TTFフォント処理")
    ttf_font, _, ttf_is_glyf = analyze_font_format(ttf_path)
    if ttf_font and ttf_is_glyf:
        ttf_data = extract_glyph_paths_ttf(ttf_font, glyph_name)
        if ttf_data:
            # TTFデータを輪郭形式に変換
            ttf_contours = []
            coords = ttf_data['coords']
            flags = ttf_data['flags']
            endPts = ttf_data['endPts']
            
            start_idx = 0
            for end_idx in endPts:
                contour_coords = coords[start_idx:end_idx + 1]
                contour_flags = flags[start_idx:end_idx + 1]
                ttf_contours.append({
                    'coords': contour_coords,
                    'flags': contour_flags
                })
                start_idx = end_idx + 1
            
            analyze_coordinate_precision(ttf_contours, "(TTF原始)")
            ttf_rounded = simulate_corner_rounding(ttf_contours)
            analyze_coordinate_precision(ttf_rounded, "(TTF角丸後)")

def main():
    """メイン処理"""
    print("OTFフォント品質診断スクリプト")
    print("=" * 50)
    
    # テスト用フォントファイルの確認
    test_files = []
    
    # 一般的なフォントファイルを探す
    common_paths = [
        "/System/Library/Fonts/",
        "/Library/Fonts/",
        "~/Library/Fonts/",
        "./",
    ]
    
    otf_files = []
    ttf_files = []
    
    for base_path in common_paths:
        try:
            expanded_path = os.path.expanduser(base_path)
            if os.path.exists(expanded_path):
                for file in os.listdir(expanded_path):
                    if file.lower().endswith('.otf'):
                        otf_files.append(os.path.join(expanded_path, file))
                    elif file.lower().endswith('.ttf'):
                        ttf_files.append(os.path.join(expanded_path, file))
        except (OSError, PermissionError):
            continue
    
    print(f"発見されたOTFファイル: {len(otf_files)}個")
    print(f"発見されたTTFファイル: {len(ttf_files)}個")
    
    if otf_files:
        print("\nOTFファイルの例:")
        for i, file in enumerate(otf_files[:5]):
            print(f"  {os.path.basename(file)}")
    
    if ttf_files:
        print("\nTTFファイルの例:")
        for i, file in enumerate(ttf_files[:5]):
            print(f"  {os.path.basename(file)}")
    
    # 比較テスト実行
    if otf_files and ttf_files:
        print(f"\n比較テストを実行します...")
        compare_font_processing(otf_files[0], ttf_files[0])
    else:
        print("\n警告: 比較用のフォントファイルが見つかりません")
        
        # 単独ファイルテスト
        if otf_files:
            print(f"OTFファイルのみでテストします: {os.path.basename(otf_files[0])}")
            otf_font, is_cff, _ = analyze_font_format(otf_files[0])
            if otf_font and is_cff:
                paths = extract_glyph_paths_cff(otf_font, 'A')
                if paths:
                    contours = convert_recording_to_contours(paths)
                    analyze_coordinate_precision(contours, "(原始)")
                    rounded = simulate_corner_rounding(contours)
                    analyze_coordinate_precision(rounded, "(角丸後)")
        
        elif ttf_files:
            print(f"TTFファイルのみでテストします: {os.path.basename(ttf_files[0])}")
            ttf_font, _, is_glyf = analyze_font_format(ttf_files[0])
            if ttf_font and is_glyf:
                data = extract_glyph_paths_ttf(ttf_font, 'A')
                if data:
                    print("TTF単独テスト完了")

if __name__ == "__main__":
    main()