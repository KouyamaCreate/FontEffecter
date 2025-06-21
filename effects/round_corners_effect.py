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
                # パス自動連結前処理
                contours = self._auto_join_contours(contours)
                
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
                        angle_threshold = self.params.get('angle_threshold', 160)
                        rounded_contour = self._round_corners_direct(
                            contour, radius, angle_threshold
                        )
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

    def _auto_join_contours(self, contours, tol=1e-3):
        """
        端点が一致する複数のcontourを自動連結する。
        tol: float, 端点一致判定の許容誤差（単位: フォント座標系）
        """
        import numpy as np

        def points_close(p1, p2):
            return np.linalg.norm(np.array(p1) - np.array(p2)) < tol

        used = [False] * len(contours)
        joined_contours = []

        for i, c in enumerate(contours):
            if used[i]:
                continue
            coords = list(c['coords'])
            flags = list(c['flags'])
            changed = True
            used[i] = True
            while changed:
                changed = False
                for j, c2 in enumerate(contours):
                    if used[j] or i == j:
                        continue
                    # 終点-始点
                    if points_close(coords[-1], c2['coords'][0]):
                        coords.extend(c2['coords'][1:])
                        flags.extend(c2['flags'][1:])
                        used[j] = True
                        changed = True
                        break
                    # 始点-終点
                    elif points_close(coords[0], c2['coords'][-1]):
                        coords = c2['coords'][:-1] + coords
                        flags = c2['flags'][:-1] + flags
                        used[j] = True
                        changed = True
                        break
                    # 始点-始点（反転して連結）
                    elif points_close(coords[0], c2['coords'][0]):
                        coords = list(reversed(c2['coords']))[:-1] + coords
                        flags = list(reversed(c2['flags']))[:-1] + flags
                        used[j] = True
                        changed = True
                        break
                    # 終点-終点（反転して連結）
                    elif points_close(coords[-1], c2['coords'][-1]):
                        coords.extend(list(reversed(c2['coords']))[1:])
                        flags.extend(list(reversed(c2['flags']))[1:])
                        used[j] = True
                        changed = True
                        break
            joined_contours.append({'coords': coords, 'flags': flags})
        return joined_contours

    def _round_corners_direct(self, contour, config_radius, angle_threshold=160):
        """
        座標データを直接操作して角丸処理を行う。
        安全なデータ操作により、元の輪郭データを保持しながら新しい輪郭を構築する。

        直線判定は、3点(p0, p1, p2)についてp1と線分p0-p2の距離が0.001以下であれば直線とみなす。
        角ごとに辺長に応じて最大半径を計算し、config.yaml指定のradiusと比較して小さい方を使用する。
        """
        import math

        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)

        if config_radius == 0 or n < 3:
            return contour

        new_coords = []
        new_flags = []
        
        for i in range(n):
            p0 = coords[i - 1]
            p1 = coords[i]
            p2 = coords[(i + 1) % n]

            # p1と線分p0-p2の距離を計算
            x0, y0 = p0
            x1, y1 = p1
            x2, y2 = p2

            # 線分p0-p2が1点に潰れている場合は距離を直接
            dx = x2 - x0
            dy = y2 - y0
            if dx == 0 and dy == 0:
                dist = math.hypot(x1 - x0, y1 - y0)
            else:
                # 線分p0-p2上の最近点を求める
                t = ((x1 - x0) * dx + (y1 - y0) * dy) / (dx * dx + dy * dy)
                t = max(0.0, min(1.0, t))
                proj_x = x0 + t * dx
                proj_y = y0 + t * dy
                dist = math.hypot(x1 - proj_x, y1 - proj_y)

            # ハイブリッド直線判定: 距離または角度で直線扱い
            ANGLE_THRESHOLD = 178.0  # ここで閾値を調整
            # 距離が非常に小さい場合は直線扱い
            if dist <= 0.001:
                new_coords.append(p1)
                new_flags.append(flags[i])
                continue

            # 動的角丸半径計算: 角ごとに最大半径を辺長から決定
            # P0-P1, P1-P2それぞれの距離
            dist1 = math.hypot(x1 - x0, y1 - y0)
            dist2 = math.hypot(x2 - x1, y2 - y1)
            max_radius = min(dist1, dist2) / 2.0
            actual_radius = min(config_radius, max_radius)

            # 以降はactual_radiusを使って角丸処理（既存のradius使用部分をactual_radiusに差し替え）
            # --- この下の角丸生成ロジックで actual_radius を利用してください ---

            # 距離が閾値を超えた場合、角度判定も追加
            v1 = (x0 - x1, y0 - y1)
            v2 = (x2 - x1, y2 - y1)
            norm1 = math.hypot(*v1)
            norm2 = math.hypot(*v2)
            if norm1 == 0 or norm2 == 0:
                new_coords.append(p1)
                new_flags.append(flags[i])
                continue
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            # 内積から角度（度数法）を算出
            cos_theta = max(-1.0, min(1.0, dot / (norm1 * norm2)))
            angle_deg = math.degrees(math.acos(cos_theta))
            # 角度が閾値以上なら直線扱い
            if angle_deg >= ANGLE_THRESHOLD:
                new_coords.append(p1)
                new_flags.append(flags[i])
                continue
            cos_angle = dot / (norm1 * norm2)
            cos_angle = min(1.0, max(-1.0, cos_angle))
            angle = math.degrees(math.acos(cos_angle))
            if angle > angle_threshold:
                new_coords.append(p1)
                new_flags.append(flags[i])
                continue

            # 角丸処理を実行
            def distance(p1, p2):
                return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

            def lerp(p1, p2, t):
                return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)
            
            # ベクトル計算
            v1 = (x0 - x1, y0 - y1)
            v2 = (x2 - x1, y2 - y1)
            norm1 = math.hypot(*v1)
            norm2 = math.hypot(*v2)
            
            if norm1 > 0 and norm2 > 0:
                # 角丸処理: 元の点を3点（T1, P1, T2）に置き換え
                l1 = min(actual_radius, norm1 * 0.5)
                l2 = min(actual_radius, norm2 * 0.5)
                
                T1 = lerp(p1, p0, l1 / norm1)
                T2 = lerp(p1, p2, l2 / norm2)
                
                # 3点を追加: T1 (オンカーブ), P1 (制御点), T2 (オンカーブ)
                new_coords.append(T1)
                new_flags.append(1)  # オンカーブ
                new_coords.append(p1)
                new_flags.append(0)  # オフカーブ（制御点）
                new_coords.append(T2)
                new_flags.append(1)  # オンカーブ
            else:
                # ベクトルが0の場合は元の点をそのまま
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        return {"coords": new_coords, "flags": new_flags}
        
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
            
            # 第一段階: 直線判定（180度に非常に近い場合、または極小角度の場合は直線とみなして除外）
            # 点数や全体サイズから自動的に直線判定閾値を推定
            straight_line_tolerance = self._estimate_straightness_threshold(coords)
            very_small_angle_threshold = 3.0  # 3度未満の極小角度も直線の一部とみなす
            
            # 180度に近い角度（ほぼ直線）
            if abs(angle_degrees - 180.0) <= straight_line_tolerance:
                continue
            
            # 極小角度の場合も直線の延長とみなす（ユーザー報告の問題に対応）
            if angle_degrees <= very_small_angle_threshold:
                continue
            
            # 第二段階: 角度閾値による判定（直線でない点に対してのみ実行）
            if angle_degrees < angle_threshold:
                l1 = min(actual_radius, norm1 * 0.5)
                l2 = min(actual_radius, norm2 * 0.5)
                
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