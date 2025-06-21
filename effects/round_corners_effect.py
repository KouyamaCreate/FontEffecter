"""
round_corners_effect.py

角丸処理エフェクトプラグイン。
グリフデータを直接操作する安全な方式で実装。
"""

from .base_effect import BaseEffect

class RoundCornersEffect(BaseEffect):
    def apply(self, font, radius=10, **kwargs):
        """
        フォントの各グリフに角丸処理を適用する。
        グリフ輪郭の角を指定した半径で丸める。
        radiusはself.params['radius']で取得することを前提とする。
        """
        import math

        print("角丸処理を開始します...")
        
        # 設定ファイルからradius取得
        radius = self.params.get('radius', radius)
        # print(f"使用する角丸半径: {radius}")
        
        # 早期リターン: radiusが0の場合は処理を完全にスキップ
        if radius == 0:
            # print("半径が0のため、角丸処理を完全にスキップします。")
            return font
        
        glyf_table = font['glyf']
        glyph_names = glyf_table.keys()
        # print(f"処理対象グリフ数: {len(glyph_names)}個")

        processed_count = 0
        
        for glyph_name in glyph_names:
            # print(f"グリフ '{glyph_name}' を処理中...")
            glyph = glyf_table[glyph_name]
            
            # コンポジットグリフはスキップ
            if glyph.isComposite():
                # print(f"  コンポジットグリフのためスキップ")
                continue
            if not hasattr(glyph, "coordinates") or glyph.numberOfContours == 0:
                # print(f"  座標データなし、または輪郭なしのためスキップ")
                continue

            try:
                # グリフデータを直接操作する安全なアプローチ
                # print(f"  グリフデータを直接操作して角丸処理を実行")
                
                # 元の座標データを取得
                if not hasattr(glyph, 'coordinates') or not glyph.coordinates:
                    # print(f"  座標データがないためスキップ")
                    continue
                
                original_coords = list(glyph.coordinates)
                original_endPts = list(glyph.endPtsOfContours)
                original_flags = list(glyph.flags)
                
                # print(f"  元のデータ - 座標数: {len(original_coords)}, 輪郭終点数: {len(original_endPts)}")
                
                # 座標データから輪郭を抽出
                contours = self._extract_contours_from_coordinates(original_coords, original_endPts, original_flags)
                # print(f"  輪郭数: {len(contours)}個")
                
                # 角丸処理を各輪郭に適用
                new_coords = []
                new_endPts = []
                new_flags = []
                
                for contour_idx, contour in enumerate(contours):
                    # print(f"    輪郭{contour_idx + 1}: 点数 {len(contour['coords'])}個")
                    
                    if len(contour['coords']) < 3:
                        # print(f"      点が少なすぎるため角丸処理をスキップ")
                        # そのまま追加
                        new_coords.extend(contour['coords'])
                        new_flags.extend(contour['flags'])
                    else:
                        # print(f"      角丸処理を実行中...")
                        rounded_contour = self._round_corners_direct(contour, radius, self.params.get('angle_threshold', 160))
                        # print(f"      角丸処理後の点数: {len(rounded_contour['coords'])}個")
                        new_coords.extend(rounded_contour['coords'])
                        new_flags.extend(rounded_contour['flags'])
                    
                    # 輪郭終点を記録
                    new_endPts.append(len(new_coords) - 1)
                
                # print(f"  処理後のデータ - 座標数: {len(new_coords)}, 輪郭終点数: {len(new_endPts)}")
                
                # 元と同じ形式でデータを作成
                from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
                
                # GlyphCoordinatesオブジェクトを作成
                coord_obj = GlyphCoordinates(new_coords)
                
                # フラグをbytearrayに変換
                flag_array = bytearray(new_flags)
                
                # 輪郭終点はlistのまま
                endPts_list = new_endPts
                
                # グリフデータを更新
                glyph.coordinates = coord_obj
                glyph.endPtsOfContours = endPts_list
                glyph.flags = flag_array
                
                # バウンディングボックスを再計算
                if new_coords:
                    x_coords = [coord[0] for coord in new_coords]
                    y_coords = [coord[1] for coord in new_coords]
                    glyph.xMin = min(x_coords)
                    glyph.xMax = max(x_coords)
                    glyph.yMin = min(y_coords)
                    glyph.yMax = max(y_coords)
                
                processed_count += 1
                print(f"  グリフ '{glyph_name}' の処理完了")
                    
            except Exception as e:
                print(f"  エラー: グリフ '{glyph_name}' の処理中に例外が発生: {str(e)}")

        print(f"角丸処理が完了しました。処理されたグリフ数: {processed_count}個")
        
        return font

    def _extract_contours_from_coordinates(self, coordinates, endPts, flags):
        """
        座標データから直接輪郭を抽出する。
        """
        contours = []
        start_idx = 0
        
        for end_idx in endPts:
            contour_coords = coordinates[start_idx:end_idx + 1]
            contour_flags = flags[start_idx:end_idx + 1]
            
            contours.append({
                'coords': contour_coords,
                'flags': contour_flags
            })
            
            start_idx = end_idx + 1
        
        return contours

    def _round_corners_direct(self, contour, radius, angle_threshold=160):
        """
        座標データを直接操作して角丸処理を行う。
        安全なデータ操作により、元の輪郭データを保持しながら新しい輪郭を構築する。
        """
        import math
        
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        if radius == 0 or n < 3:
            return contour
        
        def distance(p1, p2):
            return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        def lerp(p1, p2, t):
            return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)

        # 角丸処理が必要な点の情報を収集（元のリストは変更しない）
        corner_modifications = []
        
        # オンカーブ点のみを抽出して角度を計算
        oncurve_points = []
        oncurve_indices = []
        
        for i, (coord, flag) in enumerate(zip(coords, flags)):
            if flag & 1:  # オンカーブ点
                oncurve_points.append(coord)
                oncurve_indices.append(i)
        
        if len(oncurve_points) < 3:
            return contour
        
        # 各オンカーブ点で角度を計算し、角丸が必要かを判定
        for i in range(len(oncurve_points)):
            original_idx = oncurve_indices[i]
            p1 = oncurve_points[(i - 1) % len(oncurve_points)]
            p2 = oncurve_points[i]
            p3 = oncurve_points[(i + 1) % len(oncurve_points)]
            
            # ベクトル計算
            v1 = (p2[0] - p1[0], p2[1] - p1[1])
            v2 = (p3[0] - p2[0], p3[1] - p2[1])
            norm1 = math.hypot(*v1)
            norm2 = math.hypot(*v2)
            
            if norm1 == 0 or norm2 == 0:
                continue
            
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            angle = math.acos(max(-1, min(1, dot / (norm1 * norm2))))
            angle_degrees = math.degrees(angle)
            
            # 角度が閾値未満の場合に角丸処理が必要
            if angle_degrees < angle_threshold:
                l1 = min(radius, norm1 * 0.5)
                l2 = min(radius, norm2 * 0.5)
                
                T1 = lerp(p2, p1, l1 / norm1)
                T2 = lerp(p2, p3, l2 / norm2)
                
                corner_modifications.append({
                    'original_idx': original_idx,
                    'replace_with': [
                        (T1, 1),      # T1 (オンカーブ)
                        (p2, 0),      # 制御点P2 (オフカーブ)
                        (T2, 1)       # T2 (オンカーブ)
                    ]
                })
        
        # 新しい輪郭データを一括で構築
        new_coords = []
        new_flags = []
        
        i = 0
        while i < n:
            # この点が角丸処理対象かチェック
            corner_mod = None
            for mod in corner_modifications:
                if mod['original_idx'] == i:
                    corner_mod = mod
                    break
            
            if corner_mod:
                # 角丸処理: 元の点を置き換え
                for coord, flag in corner_mod['replace_with']:
                    new_coords.append(coord)
                    new_flags.append(flag)
            else:
                # 通常の点: そのまま保持（オンカーブ・オフカーブ問わず）
                new_coords.append(coords[i])
                new_flags.append(flags[i])
            
            i += 1
        
        return {
            'coords': new_coords,
            'flags': new_flags
        }