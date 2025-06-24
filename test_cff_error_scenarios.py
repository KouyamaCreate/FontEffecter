#!/usr/bin/env python3
"""
CFFフォントでnominalWidthXエラーが発生する可能性のあるシナリオをテスト
"""

import sys
import os

def test_cff_error_scenarios():
    """CFFフォントでエラーが発生する可能性のあるシナリオをテスト"""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.pens.t2CharStringPen import T2CharStringPen
        from fontTools.pens.recordingPen import RecordingPen
        
        print("=== CFF エラーシナリオテスト ===")
        
        # テスト1: T2CharStringPenでのPrivateDict問題
        print("\n--- テスト1: T2CharStringPen作成時のPrivateDict ---")
        try:
            # 通常の作成
            t2_pen = T2CharStringPen(width=1000, glyphSet=None)
            print("✓ T2CharStringPen作成成功")
            
            # CharStringを取得
            char_string = t2_pen.getCharString()
            print(f"✓ CharString取得成功: {char_string}")
            
            # PrivateDictアクセステスト
            if hasattr(char_string, 'private'):
                private = char_string.private
                print(f"private属性: {private}")
                
                if private is not None:
                    # nominalWidthXアクセステスト
                    try:
                        nominal_width = private.nominalWidthX
                        print(f"✓ nominalWidthX取得成功: {nominal_width}")
                    except AttributeError as e:
                        print(f"✗ nominalWidthXアクセスエラー: {e}")
                        return "T2CharStringPen", e
                else:
                    print("✗ private is None")
                    return "T2CharStringPen", "private is None"
            else:
                print("private属性なし")
                
        except Exception as e:
            print(f"✗ T2CharStringPenテストエラー: {e}")
            return "T2CharStringPen", e
        
        # テスト2: 空のCharStringでのPrivateDict問題
        print("\n--- テスト2: 空のCharString ---")
        try:
            t2_pen = T2CharStringPen(width=0, glyphSet=None)
            # 何も描画せずにCharStringを取得
            char_string = t2_pen.getCharString()
            
            if hasattr(char_string, 'private') and char_string.private is not None:
                try:
                    nominal_width = char_string.private.nominalWidthX
                    print(f"✓ 空のCharStringでnominalWidthX取得成功: {nominal_width}")
                except AttributeError as e:
                    print(f"✗ 空のCharStringでnominalWidthXエラー: {e}")
                    return "EmptyCharString", e
            else:
                print("空のCharStringでprivateがNone")
                
        except Exception as e:
            print(f"✗ 空のCharStringテストエラー: {e}")
            return "EmptyCharString", e
        
        # テスト3: 複雑なパスでのCharString作成
        print("\n--- テスト3: 複雑なパスでのCharString作成 ---")
        try:
            t2_pen = T2CharStringPen(width=500, glyphSet=None)
            
            # 複雑なパスを描画
            t2_pen.moveTo((100, 100))
            t2_pen.lineTo((200, 100))
            t2_pen.qCurveTo((250, 150), (200, 200))
            t2_pen.lineTo((100, 200))
            t2_pen.closePath()
            
            char_string = t2_pen.getCharString()
            
            if hasattr(char_string, 'private') and char_string.private is not None:
                try:
                    nominal_width = char_string.private.nominalWidthX
                    print(f"✓ 複雑なパスでnominalWidthX取得成功: {nominal_width}")
                except AttributeError as e:
                    print(f"✗ 複雑なパスでnominalWidthXエラー: {e}")
                    return "ComplexPath", e
            else:
                print("複雑なパスでprivateがNone")
                
        except Exception as e:
            print(f"✗ 複雑なパステストエラー: {e}")
            return "ComplexPath", e
        
        print("\n✓ すべてのシナリオテストが完了しました")
        return None, None
        
    except Exception as e:
        print(f"テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()
        return "TestExecution", e

def test_font_loading_scenarios():
    """異なるフォント読み込みシナリオでのテスト"""
    print("\n=== フォント読み込みシナリオテスト ===")
    
    # TTCファイルの個別フォント読み込み
    ttc_fonts = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Times.ttc"
    ]
    
    for ttc_path in ttc_fonts:
        if os.path.exists(ttc_path):
            print(f"\n--- {ttc_path} ---")
            try:
                from fontTools.ttLib import TTFont
                
                # TTCファイルの場合、フォント数を確認
                try:
                    font = TTFont(ttc_path, fontNumber=0)
                    print(f"✓ フォント0読み込み成功")
                    
                    # CFFテーブルの確認
                    has_cff = 'CFF ' in font
                    print(f"CFFテーブル: {has_cff}")
                    
                    if has_cff:
                        # 角丸処理テスト
                        from effects.round_corners_effect import RoundCornersEffect
                        params = {'radius': 2, 'angle_threshold': 160}
                        effect = RoundCornersEffect(params)
                        
                        try:
                            result_font = effect.apply(font, radius=2)
                            print("✓ 角丸処理成功")
                        except AttributeError as e:
                            if "nominalWidthX" in str(e):
                                print(f"✗ nominalWidthXエラー発生: {e}")
                                return ttc_path, e
                            else:
                                print(f"✗ 別のAttributeError: {e}")
                        except Exception as e:
                            print(f"✗ その他のエラー: {e}")
                    
                except Exception as e:
                    print(f"フォント読み込みエラー: {e}")
                    
            except Exception as e:
                print(f"TTCファイル処理エラー: {e}")
    
    return None, None

def main():
    print("CFFフォントのnominalWidthXエラーシナリオテストを開始...")
    
    # シナリオ1: T2CharStringPenでのエラー
    scenario, error = test_cff_error_scenarios()
    if error:
        print(f"\nエラーが発生したシナリオ: {scenario}")
        print(f"エラー: {error}")
        return
    
    # シナリオ2: フォント読み込みでのエラー
    font_path, error = test_font_loading_scenarios()
    if error:
        print(f"\nエラーが発生したフォント: {font_path}")
        print(f"エラー: {error}")
        return
    
    print("\n✓ すべてのシナリオテストでエラーは発生しませんでした")

if __name__ == "__main__":
    main()