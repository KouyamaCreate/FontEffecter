#!/usr/bin/env python3
"""
T2CharStringPenの問題を詳細調査
nominalWidthXエラーの原因を特定
"""

import os
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

def test_t2charstring_issue():
    """T2CharStringPenの問題を調査"""
    
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
    
    print(f"=== T2CharStringPen問題調査 ===")
    print(f"テストフォント: {font_file}")
    
    try:
        font = TTFont(font_file)
        
        # CFFテーブル情報を詳細に調査
        cff_table = font['CFF ']
        cff = cff_table.cff
        topDict = cff.topDictIndex[0]
        charStrings = topDict.CharStrings
        
        print(f"✓ CFFテーブル構造:")
        print(f"  TopDict: {topDict}")
        print(f"  CharStrings: {len(charStrings)} グリフ")
        
        # PrivateDictの調査
        if hasattr(topDict, 'Private') and topDict.Private:
            private_dict = topDict.Private
            print(f"  PrivateDict: {private_dict}")
            print(f"    nominalWidthX: {getattr(private_dict, 'nominalWidthX', 'なし')}")
            print(f"    defaultWidthX: {getattr(private_dict, 'defaultWidthX', 'なし')}")
        else:
            print(f"  PrivateDict: なし")
        
        # 利用可能なグリフから実際に形状があるものを探す
        available_glyphs = list(charStrings.keys())
        test_glyphs = []
        
        print(f"\n=== グリフ検索 ===")
        for glyph_name in available_glyphs[:20]:  # 最初の20個をチェック
            try:
                charString = charStrings[glyph_name]
                pen = RecordingPen()
                charString.draw(pen)
                
                if pen.value:  # パスデータがある
                    test_glyphs.append(glyph_name)
                    print(f"✓ {glyph_name}: {len(pen.value)} コマンド")
                    if len(test_glyphs) >= 5:  # 5個見つかったら終了
                        break
                else:
                    print(f"- {glyph_name}: パスデータなし")
            except Exception as e:
                print(f"❌ {glyph_name}: エラー {e}")
        
        print(f"\nテスト対象グリフ: {test_glyphs}")
        
        # 各グリフでT2CharStringPenをテスト
        for glyph_name in test_glyphs:
            print(f"\n{'='*50}")
            print(f"グリフ '{glyph_name}' のT2CharStringPenテスト")
            print(f"{'='*50}")
            
            try:
                # 元のCharStringを取得
                original_charstring = charStrings[glyph_name]
                print(f"✓ 元のCharString取得成功")
                
                # 元のCharStringの属性を調査
                print(f"元のCharString属性:")
                print(f"  width: {getattr(original_charstring, 'width', 'なし')}")
                print(f"  private: {getattr(original_charstring, 'private', 'なし')}")
                
                # 元のパスデータを取得
                original_pen = RecordingPen()
                original_charstring.draw(original_pen)
                original_commands = original_pen.value
                
                print(f"✓ 元のパスコマンド数: {len(original_commands)}")
                
                # 異なるパラメータでT2CharStringPenをテスト
                test_cases = [
                    {"width": None, "glyphSet": None, "name": "デフォルト"},
                    {"width": 0, "glyphSet": None, "name": "width=0"},
                    {"width": getattr(original_charstring, 'width', 0), "glyphSet": None, "name": "元のwidth"},
                ]
                
                for i, test_case in enumerate(test_cases):
                    print(f"\n--- テストケース {i+1}: {test_case['name']} ---")
                    
                    try:
                        # T2CharStringPenを作成
                        t2_pen = T2CharStringPen(
                            width=test_case['width'], 
                            glyphSet=test_case['glyphSet']
                        )
                        
                        # 簡単なパスを描画
                        t2_pen.moveTo((100, 100))
                        t2_pen.lineTo((200, 100))
                        t2_pen.lineTo((200, 200))
                        t2_pen.lineTo((100, 200))
                        t2_pen.closePath()
                        
                        # CharStringを取得
                        new_charstring = t2_pen.getCharString()
                        print(f"✓ CharString作成成功")
                        
                        # 新しいCharStringの属性を調査
                        print(f"新しいCharString属性:")
                        print(f"  width: {getattr(new_charstring, 'width', 'なし')}")
                        print(f"  private: {getattr(new_charstring, 'private', 'なし')}")
                        
                        # PrivateDictを設定してみる
                        if hasattr(topDict, 'Private') and topDict.Private:
                            try:
                                new_charstring.private = topDict.Private
                                print(f"✓ PrivateDict設定成功")
                            except Exception as private_error:
                                print(f"❌ PrivateDict設定エラー: {private_error}")
                        
                        # 再描画テスト
                        test_pen = RecordingPen()
                        new_charstring.draw(test_pen)
                        print(f"✓ 再描画成功: {len(test_pen.value)} コマンド")
                        
                    except Exception as case_error:
                        print(f"❌ テストケース {i+1} エラー: {case_error}")
                        import traceback
                        traceback.print_exc()
                
                # 元のパスデータでT2CharStringPenをテスト
                print(f"\n--- 元のパスデータ再現テスト ---")
                try:
                    t2_pen = T2CharStringPen(
                        width=getattr(original_charstring, 'width', 0), 
                        glyphSet=None
                    )
                    
                    # 元のパスコマンドを再現
                    for cmd, pts in original_commands:
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
                    recreated_charstring = t2_pen.getCharString()
                    print(f"✓ 元のパス再現成功")
                    
                    # PrivateDictを設定
                    if hasattr(topDict, 'Private') and topDict.Private:
                        recreated_charstring.private = topDict.Private
                    
                    # 再描画テスト
                    verify_pen = RecordingPen()
                    recreated_charstring.draw(verify_pen)
                    print(f"✓ 再描画検証成功: {len(verify_pen.value)} コマンド")
                    
                    # 座標比較
                    def extract_coordinates(pen_value):
                        coords = []
                        for cmd, pts in pen_value:
                            if cmd in ["moveTo", "lineTo"]:
                                coords.extend(pts)
                            elif cmd in ["qCurveTo", "curveTo"]:
                                coords.extend(pts)
                        return coords
                    
                    original_coords = extract_coordinates(original_commands)
                    recreated_coords = extract_coordinates(verify_pen.value)
                    
                    print(f"座標数比較: 元={len(original_coords)}, 再現={len(recreated_coords)}")
                    
                    if original_coords and recreated_coords:
                        # 最初の数点を比較
                        print(f"座標比較（最初の5点）:")
                        min_len = min(5, len(original_coords), len(recreated_coords))
                        for i in range(min_len):
                            orig = original_coords[i]
                            recr = recreated_coords[i]
                            print(f"  点{i}: 元{orig} → 再現{recr}")
                    
                except Exception as recreate_error:
                    print(f"❌ 元のパス再現エラー: {recreate_error}")
                    import traceback
                    traceback.print_exc()
                
            except Exception as glyph_error:
                print(f"❌ グリフ '{glyph_name}' テストエラー: {glyph_error}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*60}")
        print("T2CharStringPen問題調査完了")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_t2charstring_issue()