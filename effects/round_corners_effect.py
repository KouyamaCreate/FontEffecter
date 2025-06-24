"""
round_corners_effect.py

角丸処理エフェクトプラグイン。
グリフデータを直接操作する安全な方式で実装。
"""

from .base_effect import BaseEffect

class RoundCornersEffect(BaseEffect):
    _warned_once = False
    
    def __init__(self, params=None):
        super().__init__(params)
        # 属性を確実に初期化
        self._boolean_ops_available = False
        
        # 動的インポートを __init__ で実行
        import importlib
        try:
            from fontTools.pens.recordingPen import RecordingPen
            from fontTools.pens.basePen import decomposeQuadraticSegment
            from fontTools.pens.ttGlyphPen import TTGlyphPen
            from fontTools.booleanOperations import BooleanGlyph, union
            self.BooleanGlyph = BooleanGlyph
            self.union = union
            self._boolean_ops_available = True
        except ImportError:
            try:
                boolean_ops_module = importlib.import_module("fontTools.booleanOperations")
                self.BooleanGlyph = boolean_ops_module.BooleanGlyph
                self.union = boolean_ops_module.union
                self._boolean_ops_available = True
                print("INFO: Successfully loaded booleanOperations via dynamic import.")
            except ImportError:
                self._boolean_ops_available = False
                print("WARNING: Path union feature failed to load. Glyphs with overlapping paths may not look correct.")
    
    def apply(self, font, radius=10, **kwargs):
        """
        フォントの各グリフに角丸処理を適用する。
        グリフ輪郭の角を指定した半径で丸める。
        radiusはself.params['radius']で取得することを前提とする。
        """
        import math
        import yaml

        print("角丸処理を開始します...")

        # 設定ファイルからradius取得
        radius = self.params.get('radius', radius)

        # 品質レベル取得（params優先、なければconfig.yamlから）
        quality_level = self.params.get('quality_level')
        if not quality_level:
            try:
                with open('config.yaml', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    quality_level = config_data.get('quality_level', 'medium')
            except Exception:
                quality_level = 'medium'
        quality_level = str(quality_level).lower()

        # 品質レベルごとの閾値
        if quality_level == 'high':
            ANGLE_THRESHOLD = 175.0
            angle_threshold = 160
            min_reduction_ratio = 0.7  # 30%以上減少で警告
        elif quality_level == 'low':
            ANGLE_THRESHOLD = 160.0
            angle_threshold = 110
            min_reduction_ratio = 0.5  # 50%以上減少で警告
        else:
            ANGLE_THRESHOLD = 170.0
            angle_threshold = 140
            min_reduction_ratio = 0.5  # 50%以上減少で警告

        # 早期リターン: radiusが0の場合は処理を完全にスキップ
        if radius == 0:
            return font

        # フォント形式の判定と対応
        has_glyf = 'glyf' in font
        has_cff = 'CFF ' in font
        
        print(f"フォント形式: {'TrueType' if has_glyf else 'OpenType/CFF' if has_cff else '不明'}")
        
        if not has_glyf and not has_cff:
            raise ValueError("サポートされていないフォント形式です。TrueType (.ttf) または OpenType/CFF (.otf) フォントを使用してください。")
        
        if has_cff:
            # OpenType/CFFフォントの処理
            return self._apply_to_cff_font(font, radius, ANGLE_THRESHOLD, angle_threshold, min_reduction_ratio, quality_level)
        else:
            # TrueTypeフォントの処理
            return self._apply_to_truetype_font(font, radius, ANGLE_THRESHOLD, angle_threshold, min_reduction_ratio, quality_level)

    def _apply_to_truetype_font(self, font, radius, ANGLE_THRESHOLD, angle_threshold, min_reduction_ratio, quality_level):
        """TrueTypeフォント用の角丸処理"""
        import math
        
        glyf_table = font['glyf']
        glyph_names = glyf_table.keys()

        processed_count = 0

        for glyph_name in glyph_names:
            glyph = glyf_table[glyph_name]

            # コンポジットグリフはスキップ
            if glyph.isComposite():
                continue
            if not hasattr(glyph, "coordinates") or glyph.numberOfContours == 0:
                continue

            try:
                # グリフデータを直接操作する安全なアプローチ

                # 元の座標データを取得
                if not hasattr(glyph, 'coordinates') or not glyph.coordinates:
                    continue

                original_coords = list(glyph.coordinates)
                original_endPts = list(glyph.endPtsOfContours)
                original_flags = list(glyph.flags)
                original_point_count = len(original_coords)

                # 座標データから輪郭を抽出
                contours = self._extract_contours_from_coordinates(original_coords, original_endPts, original_flags)
                # パス自動連結前処理
                contours = self._auto_join_contours(contours)

                # パス統合（Union）処理の可否判定
                use_union = self._boolean_ops_available

                if use_union:
                    from fontTools.pens.recordingPen import RecordingPen
                    from fontTools.pens.basePen import decomposeQuadraticSegment
                    from fontTools.pens.ttGlyphPen import TTGlyphPen
                    from fontTools.booleanOperations import BooleanGlyph, union

                    def contours_to_BooleanGlyph(contours):
                        bg = BooleanGlyph()
                        for contour in contours:
                            coords = contour['coords']
                            flags = contour['flags']
                            if not coords or len(coords) < 2:
                                continue
                            pen = bg.getPen()
                            pen.moveTo(coords[0])
                            i = 1
                            while i < len(coords):
                                is_on_curve = flags[i] & 1
                                if is_on_curve:
                                    pen.lineTo(coords[i])
                                else:
                                    if i + 1 < len(coords) and (flags[i + 1] & 1):
                                        pen.qCurveTo(coords[i], coords[i + 1])
                                        i += 1
                                    else:
                                        mid = (
                                            (coords[i - 1][0] + coords[i][0]) / 2,
                                            (coords[i - 1][1] + coords[i][1]) / 2
                                        )
                                        pen.qCurveTo(coords[i], mid)
                                i += 1
                            pen.closePath()
                        return bg

                    def BooleanGlyph_to_contours(bg):
                        pen = RecordingPen()
                        bg.draw(pen)
                        contours = []
                        current_coords = []
                        current_flags = []
                        for cmd, pts in pen.value:
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
                                    current_flags.append(0)  # off-curve
                                current_coords.append(pts[-1])
                                current_flags.append(1)  # end on-curve
                            elif cmd == "closePath":
                                pass
                            elif cmd == "endPath":
                                pass
                        if current_coords:
                            contours.append({'coords': current_coords, 'flags': current_flags})
                        return contours

                    bg = contours_to_BooleanGlyph(contours)
                    union_bg = BooleanGlyph()
                    union(bg, union_bg)
                    unified_contours = BooleanGlyph_to_contours(union_bg)
                else:
                    if not RoundCornersEffect._warned_once:
                        print("WARNING: Path union feature failed to load. Glyphs with overlapping paths may not look correct. Continuing with basic corner rounding.")
                        RoundCornersEffect._warned_once = True
                    unified_contours = contours

                # 角丸処理を各輪郭に適用
                new_coords = []
                new_endPts = []
                new_flags = []

                for contour_idx, contour in enumerate(unified_contours):
                    if len(contour['coords']) < 3:
                        new_coords.extend(contour['coords'])
                        new_flags.extend(contour['flags'])
                    else:
                        # 品質レベルごとに角度閾値を適用
                        rounded_contour = self._round_corners_direct(
                            contour, radius, angle_threshold if quality_level != 'high' else ANGLE_THRESHOLD
                        )
                        new_coords.extend(rounded_contour['coords'])
                        new_flags.extend(rounded_contour['flags'])

                    # 輪郭終点を記録
                    new_endPts.append(len(new_coords) - 1)

                # 頂点数比較（品質維持チェック）
                new_point_count = len(new_coords)
                if original_point_count > 0:
                    reduction_ratio = new_point_count / original_point_count
                    if reduction_ratio < min_reduction_ratio:
                        print(f"[品質警告] グリフ '{glyph_name}': 頂点数が{int((1-reduction_ratio)*100)}%減少（{original_point_count}→{new_point_count}）。品質低下の可能性あり、処理をスキップします。")
                        continue

                # データ整合性チェック
                if len(new_coords) != len(new_flags):
                    print(f"  [ERROR] 座標数とフラグ数が一致しません: coords={len(new_coords)}, flags={len(new_flags)}")

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

        print(f"TrueTypeフォントの角丸処理が完了しました。処理されたグリフ数: {processed_count}個")
        
        return font

    def _apply_to_cff_font(self, font, radius, ANGLE_THRESHOLD, angle_threshold, min_reduction_ratio, quality_level):
        """OpenType/CFFフォント用の角丸処理 - T2CharString座標変化対応版"""
        import math
        from fontTools.pens.recordingPen import RecordingPen
        from fontTools.pens.t2CharStringPen import T2CharStringPen
        
        print("OpenType/CFFフォントの角丸処理を開始します（T2CharString座標変化対応版）...")
        
        try:
            cff_table = font['CFF ']
            cff = cff_table.cff
            topDict = cff.topDictIndex[0]
            charStrings = topDict.CharStrings
        except Exception as cff_error:
            print(f"エラー: CFFテーブルの読み込みに失敗しました: {cff_error}")
            return font
        
        processed_count = 0
        
        # T2CharString座標変化を考慮した最適化設定
        if quality_level == 'high':
            effective_angle_threshold = 160  # より多くの角を処理
            effective_radius = radius * 0.8  # より積極的な半径
            min_corner_radius = 1.0
        elif quality_level == 'low':
            effective_angle_threshold = 120  # 中程度の角まで処理
            effective_radius = radius * 0.5  # 控えめな半径
            min_corner_radius = 2.0
        else:  # medium
            effective_angle_threshold = 150  # 多くの角を処理
            effective_radius = radius * 0.6  # バランスの取れた半径
            min_corner_radius = 1.0
        
        for glyph_name in charStrings.keys():
            try:
                # CFFグリフからパスデータを取得
                charString = charStrings[glyph_name]
                
                # RecordingPenを使ってパスデータを記録
                pen = RecordingPen()
                charString.draw(pen)
                
                # パスデータから輪郭を抽出
                contours = self._extract_contours_from_recording_pen(pen.value)
                
                if not contours:
                    continue
                
                # パス自動連結前処理
                contours = self._auto_join_contours(contours)
                
                # オリジナル頂点数（全contour合計）
                original_point_count = sum(len(c['coords']) for c in contours)

                # T2CharString対応の角丸処理を各輪郭に適用
                rounded_contours = []
                corners_processed = 0
                
                for contour in contours:
                    if len(contour['coords']) >= 3:
                        # T2CharString対応の角丸処理を使用
                        rounded_contour, corner_count = self._round_corners_t2charstring_compatible(
                            contour, effective_radius, effective_angle_threshold, min_corner_radius
                        )
                        rounded_contours.append(rounded_contour)
                        corners_processed += corner_count
                    else:
                        rounded_contours.append(contour)

                # 角丸処理が実際に行われた場合のみ更新
                if corners_processed > 0:
                    # 新しい頂点数（全contour合計）
                    new_point_count = sum(len(c['coords']) for c in rounded_contours)
                    
                    # 品質チェックを緩和（T2CharStringの座標変化を考慮）
                    if original_point_count > 0:
                        reduction_ratio = new_point_count / original_point_count
                        # より緩い品質チェック（30%減少まで許容）
                        if reduction_ratio < 0.3:
                            print(f"[品質警告] グリフ '{glyph_name}': 頂点数が{int((1-reduction_ratio)*100)}%減少（{original_point_count}→{new_point_count}）。処理をスキップします。")
                            continue

                    # 新しいCharStringを作成
                    try:
                        # 元のCharStringの幅を取得
                        original_width = getattr(charString, 'width', 0)
                        
                        # 元のPrivateDictを取得（安全にアクセス）
                        original_private = None
                        if hasattr(charString, 'private') and charString.private is not None:
                            original_private = charString.private
                        
                        t2_pen = T2CharStringPen(width=original_width, glyphSet=None)
                        
                        for contour in rounded_contours:
                            coords = contour['coords']
                            flags = contour['flags']
                            
                            if not coords:
                                continue
                            
                            # パスを描画
                            t2_pen.moveTo(coords[0])
                            
                            i = 1
                            while i < len(coords):
                                if i >= len(flags):
                                    break
                                
                                if flags[i] & 1:  # オンカーブ点
                                    t2_pen.lineTo(coords[i])
                                else:  # オフカーブ点（制御点）
                                    if i + 1 < len(coords) and i + 1 < len(flags) and (flags[i + 1] & 1):
                                        # 二次ベジェ曲線
                                        t2_pen.qCurveTo(coords[i], coords[i + 1])
                                        i += 1
                                    else:
                                        # 単独の制御点処理を改善
                                        t2_pen.lineTo(coords[i])
                                i += 1
                            
                            t2_pen.closePath()
                        
                        # 新しいCharStringで置き換え
                        new_charstring = t2_pen.getCharString()
                        
                        # 属性を適切に設定
                        new_charstring.width = original_width
                        
                        # PrivateDictを安全に設定
                        if original_private is not None:
                            try:
                                new_charstring.private = original_private
                            except Exception as private_error:
                                print(f"    警告: PrivateDict設定エラー: {private_error}")
                                self._set_default_private_dict(new_charstring, original_private)
                        else:
                            self._set_default_private_dict(new_charstring, None)
                        
                        charStrings[glyph_name] = new_charstring
                        processed_count += 1
                        print(f"  グリフ '{glyph_name}' の処理完了 ({corners_processed}角を角丸化)")
                        
                    except Exception as char_error:
                        print(f"    CharString作成エラー: {char_error}")
                        continue
                
            except Exception as e:
                print(f"  エラー: グリフ '{glyph_name}' の処理中に例外が発生: {str(e)}")
        
        print(f"OpenType/CFFフォントの角丸処理が完了しました。処理されたグリフ数: {processed_count}個")
        
        return font

    def _round_corners_cff_precision(self, contour, config_radius, angle_threshold=160):
        """
        CFF専用の高精度座標角丸処理
        座標精度を制御し、整数座標との混在を避ける
        """
        import math
        
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        if config_radius == 0 or n < 3:
            return contour
        
        # CFF座標の精度レベルを分析
        precision_level = self._analyze_cff_coordinate_precision(coords)
        print(f"    CFF座標精度レベル: {precision_level}")
        
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
            
            # 直線判定（CFF用の厳密な閾値）
            if angle_deg >= 178.0:  # CFF用の直線閾値
                new_coords.append(p1)
                new_flags.append(flags[i])
                continue
            
            # 角丸判定
            if angle_deg < angle_threshold:
                # 動的半径計算
                max_radius = min(norm1, norm2) / 2.0
                actual_radius = min(config_radius, max_radius)
                
                # 高精度座標計算（精度制御付き）
                l1 = min(actual_radius, norm1 * 0.5)
                l2 = min(actual_radius, norm2 * 0.5)
                
                # 座標計算（精度制御）
                T1 = self._calculate_precise_coordinate(p1, p0, l1 / norm1, precision_level)
                T2 = self._calculate_precise_coordinate(p1, p2, l2 / norm2, precision_level)
                
                # 3点を追加: T1 (オンカーブ), P1 (制御点), T2 (オンカーブ)
                new_coords.append(T1)
                new_flags.append(1)  # オンカーブ
                new_coords.append(p1)
                new_flags.append(0)  # オフカーブ（制御点）
                new_coords.append(T2)
                new_flags.append(1)  # オンカーブ
            else:
                # 通常の点をそのまま保持
                new_coords.append(p1)
                new_flags.append(flags[i])
        
        return {"coords": new_coords, "flags": new_flags}
    
    def _round_corners_t2charstring_compatible(self, contour, radius, angle_threshold, min_radius):
        """
        T2CharString互換の角丸処理
        座標変化を前提とした最適化実装
        """
        import math
        
        coords = contour['coords']
        flags = contour['flags']
        n = len(coords)
        
        if radius == 0 or n < 3:
            return contour, 0
        
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
            
            # 角丸判定（より緩い条件）
            if angle_deg < angle_threshold and angle_deg > 3:
                # 動的半径計算
                max_radius = min(norm1, norm2) / 3.0
                actual_radius = min(radius, max_radius)
                
                if actual_radius >= min_radius:
                    # T2CharString対応の角丸処理
                    corner_result = self._create_t2charstring_compatible_corner(
                        p0, p1, p2, actual_radius, norm1, norm2, angle_deg
                    )
                    
                    if corner_result:
                        new_coords.extend(corner_result['coords'])
                        new_flags.extend(corner_result['flags'])
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
        
        return {"coords": new_coords, "flags": new_flags}, corners_rounded
    
    def _create_t2charstring_compatible_corner(self, p0, p1, p2, radius, norm1, norm2, angle_deg):
        """T2CharString互換の角丸コーナーを作成"""
        import math
        
        v1 = (p0[0] - p1[0], p0[1] - p1[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        
        # 角度に応じて処理方法を選択（範囲を拡大）
        if angle_deg < 30:
            # 非常に鋭角 - 単純な面取り（直線）
            l1 = min(radius * 0.2, norm1 * 0.1)
            l2 = min(radius * 0.2, norm2 * 0.1)
            
            T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
            T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
            
            return {
                'coords': [T1, T2],
                'flags': [1, 1]  # 直線接続
            }
        
        elif angle_deg < 90:
            # 鋭角から中程度 - 控えめなベジェ曲線
            l1 = min(radius * 0.3, norm1 * 0.15)
            l2 = min(radius * 0.3, norm2 * 0.15)
            
            T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
            T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
            
            # 制御点を保守的に設定（T2CharStringの座標変化を考慮）
            ctrl_factor = 0.3
            ctrl_x = p1[0] + (T1[0] - p1[0] + T2[0] - p1[0]) * ctrl_factor * 0.5
            ctrl_y = p1[1] + (T1[1] - p1[1] + T2[1] - p1[1]) * ctrl_factor * 0.5
            
            return {
                'coords': [T1, (ctrl_x, ctrl_y), T2],
                'flags': [1, 0, 1]  # ベジェ曲線
            }
        
        elif angle_deg < 150:
            # 中程度から鈍角 - 標準的なベジェ曲線
            l1 = min(radius * 0.4, norm1 * 0.2)
            l2 = min(radius * 0.4, norm2 * 0.2)
            
            T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
            T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
            
            # より滑らかな制御点
            ctrl_factor = 0.4
            ctrl_x = p1[0] + (T1[0] - p1[0] + T2[0] - p1[0]) * ctrl_factor * 0.5
            ctrl_y = p1[1] + (T1[1] - p1[1] + T2[1] - p1[1]) * ctrl_factor * 0.5
            
            return {
                'coords': [T1, (ctrl_x, ctrl_y), T2],
                'flags': [1, 0, 1]  # ベジェ曲線
            }
        
        elif angle_deg < 170:
            # 鈍角 - 軽微な角丸
            l1 = min(radius * 0.2, norm1 * 0.1)
            l2 = min(radius * 0.2, norm2 * 0.1)
            
            T1 = (p1[0] + v1[0] * l1 / norm1, p1[1] + v1[1] * l1 / norm1)
            T2 = (p1[0] + v2[0] * l2 / norm2, p1[1] + v2[1] * l2 / norm2)
            
            # 軽微な制御点
            ctrl_factor = 0.2
            ctrl_x = p1[0] + (T1[0] - p1[0] + T2[0] - p1[0]) * ctrl_factor * 0.5
            ctrl_y = p1[1] + (T1[1] - p1[1] + T2[1] - p1[1]) * ctrl_factor * 0.5
            
            return {
                'coords': [T1, (ctrl_x, ctrl_y), T2],
                'flags': [1, 0, 1]  # ベジェ曲線
            }
        
        else:
            # 非常に鈍角（170度以上） - 処理しない
            return None
    
    def _analyze_cff_coordinate_precision(self, coords):
        """CFF座標の精度レベルを分析"""
        if not coords:
            return 0
        
        max_precision = 0
        float_count = 0
        
        for coord in coords:
            x, y = coord
            
            # X座標の精度
            if x != int(x):
                float_count += 1
                x_str = str(x)
                if '.' in x_str:
                    x_precision = len(x_str.split('.')[-1])
                    max_precision = max(max_precision, x_precision)
            
            # Y座標の精度
            if y != int(y):
                float_count += 1
                y_str = str(y)
                if '.' in y_str:
                    y_precision = len(y_str.split('.')[-1])
                    max_precision = max(max_precision, y_precision)
        
        # 精度レベルを決定
        if float_count == 0:
            return 0  # 全て整数座標
        elif max_precision <= 3:
            return 1  # 低精度浮動小数点
        elif max_precision <= 6:
            return 2  # 中精度浮動小数点
        else:
            return 3  # 高精度浮動小数点
    
    def _calculate_precise_coordinate(self, base_point, target_point, ratio, precision_level):
        """精度制御付きの座標計算"""
        import math
        
        # 基本計算
        x = base_point[0] + (target_point[0] - base_point[0]) * ratio
        y = base_point[1] + (target_point[1] - base_point[1]) * ratio
        
        # 精度レベルに応じて座標を調整
        if precision_level == 0:
            # 整数座標を維持
            x = round(x)
            y = round(y)
        elif precision_level == 1:
            # 低精度（小数点以下2桁）
            x = round(x, 2)
            y = round(y, 2)
        elif precision_level == 2:
            # 中精度（小数点以下4桁）
            x = round(x, 4)
            y = round(y, 4)
        else:
            # 高精度の場合でも6桁に制限
            x = round(x, 6)
            y = round(y, 6)
        
        return (x, y)

    def _extract_contours_from_recording_pen(self, pen_value):
        """RecordingPenの記録からcontourデータを抽出"""
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
                # 簡単な実装として制御点を追加
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

    def _contours_to_skia_path(self, contours):
        """
        fontToolsの輪郭データをskia.Pathオブジェクトに変換する。
        """
        from pathops import Path
        
        path = Path()
        
        for contour in contours:
            coords = contour['coords']
            flags = contour['flags']
            
            if not coords:
                continue
                
            # 最初の点に移動
            path.moveTo(*coords[0])
            
            i = 1
            while i < len(coords):
                if flags[i] & 1:  # オンカーブ点
                    path.lineTo(*coords[i])
                    i += 1
                else:  # オフカーブ点（制御点）
                    if i + 1 < len(coords) and flags[i + 1] & 1:
                        # 二次ベジェ曲線: 制御点 + 終点
                        path.quadTo(*coords[i], *coords[i + 1])
                        i += 2
                    elif i + 2 < len(coords) and flags[i + 1] == 0 and flags[i + 2] & 1:
                        # 三次ベジェ曲線: 制御点1 + 制御点2 + 終点
                        path.cubicTo(*coords[i], *coords[i + 1], *coords[i + 2])
                        i += 3
                    else:
                        # 単独の制御点の場合は直線として処理
                        if i + 1 < len(coords):
                            path.lineTo(*coords[i + 1])
                            i += 2
                        else:
                            i += 1
            
            # 輪郭を閉じる（pathopsでは close() メソッドを使用）
            path.close()
        
        return path

    def _skia_path_to_contours(self, skia_path):
        """
        skia.PathオブジェクトをfontToolsの輪郭データに変換する。
        """
        contours = []
        
        # pathopsのPathからセグメント情報を取得
        # 簡単な実装として、pathの描画コマンドを解析
        try:
            # skia-pathopsのPathオブジェクトから座標を抽出
            # 実際の実装では、pathの内部構造にアクセスする必要がある
            # ここでは基本的な変換のみ実装
            
            # pathの境界ボックスから基本的な矩形パスを生成（暫定実装）
            bounds = skia_path.getBounds()
            if bounds:
                x_min, y_min, x_max, y_max = bounds
                
                # 矩形の4つの角の座標
                coords = [
                    (x_min, y_min),
                    (x_max, y_min),
                    (x_max, y_max),
                    (x_min, y_max)
                ]
                flags = [1, 1, 1, 1]  # すべてオンカーブ点
                
                contours.append({
                    'coords': coords,
                    'flags': flags
                })
        except Exception as e:
            print(f"警告: skia.Pathの変換中にエラーが発生しました: {e}")
            # エラーの場合は空の輪郭を返す
            contours = []
        
        return contours

    def _estimate_straightness_threshold(self, coords):
        """
        座標データから直線判定の閾値を推定する。
        点数や全体サイズに基づいて適切な閾値を計算する。
        """
        import math
        
        if not coords or len(coords) < 2:
            return 1.0  # デフォルト値
        
        # 座標の範囲を計算
        x_coords = [coord[0] for coord in coords]
        y_coords = [coord[1] for coord in coords]
        
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        
        # 全体のサイズ
        total_size = math.hypot(x_range, y_range)
        
        # 点数に基づく調整
        num_points = len(coords)
        
        # 基本閾値: サイズが大きいほど、点数が多いほど厳しく
        base_threshold = 0.5
        size_factor = min(2.0, total_size / 1000.0)  # サイズに応じた調整
        point_factor = min(2.0, num_points / 50.0)   # 点数に応じた調整
        
        threshold = base_threshold + size_factor + point_factor
        
        # 最小値と最大値を制限
        return max(0.1, min(5.0, threshold))

    def _set_default_private_dict(self, charstring, original_private):
        """
        CharStringに安全なデフォルトPrivateDictを設定する
        """
        try:
            from fontTools.cffLib import PrivateDict
            
            # 新しいPrivateDictを作成
            private_dict = PrivateDict()
            
            if original_private is not None:
                # 元のPrivateDictから値をコピー
                try:
                    if hasattr(original_private, 'nominalWidthX'):
                        private_dict.nominalWidthX = original_private.nominalWidthX
                    else:
                        private_dict.nominalWidthX = 0
                        
                    if hasattr(original_private, 'defaultWidthX'):
                        private_dict.defaultWidthX = original_private.defaultWidthX
                    else:
                        private_dict.defaultWidthX = 1000
                        
                    # その他の重要な属性もコピー
                    for attr in ['Subrs', 'BlueValues', 'OtherBlues', 'FamilyBlues', 'FamilyOtherBlues']:
                        if hasattr(original_private, attr):
                            setattr(private_dict, attr, getattr(original_private, attr))
                            
                except Exception as copy_error:
                    print(f"    警告: PrivateDict属性コピーエラー: {copy_error}")
                    # コピーに失敗した場合はデフォルト値を設定
                    private_dict.nominalWidthX = 0
                    private_dict.defaultWidthX = 1000
            else:
                # デフォルト値を設定
                private_dict.nominalWidthX = 0
                private_dict.defaultWidthX = 1000
            
            # CharStringにPrivateDictを設定
            charstring.private = private_dict
            
        except Exception as e:
            print(f"    警告: デフォルトPrivateDict作成エラー: {e}")
            # 最後の手段として、空のオブジェクトを作成
            try:
                class SafePrivateDict:
                    def __init__(self):
                        self.nominalWidthX = 0
                        self.defaultWidthX = 1000
                
                charstring.private = SafePrivateDict()
            except Exception as fallback_error:
                print(f"    エラー: フォールバックPrivateDict作成失敗: {fallback_error}")