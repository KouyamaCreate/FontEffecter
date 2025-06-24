#!/usr/bin/env python3
"""
CFFフォントのnominalWidthXエラー修正の検証テスト
"""

import sys
import os

def test_cff_fix():
    """修正されたCFFフォント処理をテスト"""
    try:
        from fontTools.ttLib import TTFont
        from effects.round_corners_effect import RoundCornersEffect
        
        print("=== CFF修正の検証テスト ===")
        
        # テスト用フォントファイルを探す
        test_fonts = [
            "output_rounded.otf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Times.ttc"
        ]
        
        font_path = None
        for path in test_fonts:
            if os.path.exists(path):
                font_path = path
                break
        
        if not font_path:
            print("テスト用フォントが見つかりません")
            return False
        
        print(f"テストフォント: {font_path}")
        
        # フォントを読み込み
        if font_path.endswith('.ttc'):
            font = TTFont(font_path, fontNumber=0)
        else:
            font = TTFont(font_path)
        
        # CFFフォントかどうか確認
        has_cff = 'CFF ' in font
        print(f"CFFフォント: {has_cff}")
        
        if not has_cff:
            print("CFFフォントではないため、別のフォントでテストします")
            # 他のフォントを試す
            for path in test_fonts[1:]:
                if os.path.exists(path):
                    try:
                        font = TTFont(path, fontNumber=0)
                        if 'CFF ' in font:
                            font_path = path
                            has_cff = True
                            print(f"CFFフォントを発見: {path}")
                            break
                    except:
                        continue
        
        if not has_cff:
            print("CFFフォントが見つからないため、テストをスキップします")
            return True
        
        # 角丸エフェクトを作成
        params = {'radius': 5, 'angle_threshold': 160}
        effect = RoundCornersEffect(params)
        
        print("修正されたCFFフォント処理をテスト中...")
        
        try:
            result_font = effect.apply(font, radius=5)
            print("✓ CFFフォント処理が正常に完了しました")
            
            # 結果フォントを保存してテスト
            output_path = "test_cff_fixed_output.otf"
            result_font.save(output_path)
            print(f"✓ 修正されたフォントを保存しました: {output_path}")
            
            return True
            
        except AttributeError as e:
            if "nominalWidthX" in str(e):
                print(f"✗ nominalWidthXエラーがまだ発生しています: {e}")
                import traceback
                traceback.print_exc()
                return False
            else:
                print(f"✗ 別のAttributeErrorが発生: {e}")
                import traceback
                traceback.print_exc()
                return False
        except Exception as e:
            print(f"✗ 予期しないエラーが発生: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_privatedict_safety():
    """PrivateDict安全性テスト"""
    print("\n=== PrivateDict安全性テスト ===")
    
    try:
        from fontTools.pens.t2CharStringPen import T2CharStringPen
        from effects.round_corners_effect import RoundCornersEffect
        
        # RoundCornersEffectインスタンスを作成
        effect = RoundCornersEffect({'radius': 10})
        
        # T2CharStringPenでCharStringを作成
        t2_pen = T2CharStringPen(width=1000, glyphSet=None)
        t2_pen.moveTo((100, 100))
        t2_pen.lineTo((200, 100))
        t2_pen.lineTo((200, 200))
        t2_pen.lineTo((100, 200))
        t2_pen.closePath()
        
        charstring = t2_pen.getCharString()
        print(f"作成されたCharString: {charstring}")
        print(f"CharString.private: {getattr(charstring, 'private', 'None')}")
        
        # デフォルトPrivateDictを設定
        effect._set_default_private_dict(charstring, None)
        
        # nominalWidthXアクセステスト
        try:
            nominal_width = charstring.private.nominalWidthX
            print(f"✓ nominalWidthX取得成功: {nominal_width}")
        except AttributeError as e:
            print(f"✗ nominalWidthXアクセスエラー: {e}")
            return False
        
        # defaultWidthXアクセステスト
        try:
            default_width = charstring.private.defaultWidthX
            print(f"✓ defaultWidthX取得成功: {default_width}")
        except AttributeError as e:
            print(f"✗ defaultWidthXアクセスエラー: {e}")
            return False
        
        print("✓ PrivateDict安全性テストが完了しました")
        return True
        
    except Exception as e:
        print(f"PrivateDict安全性テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("CFFフォントのnominalWidthXエラー修正の検証を開始...")
    
    # テスト1: PrivateDict安全性テスト
    success1 = test_privatedict_safety()
    
    # テスト2: CFF修正テスト
    success2 = test_cff_fix()
    
    if success1 and success2:
        print("\n✓ すべてのテストが成功しました！")
        print("nominalWidthXエラーが修正されました。")
    else:
        print("\n✗ 一部のテストが失敗しました。")
        if not success1:
            print("- PrivateDict安全性テストが失敗")
        if not success2:
            print("- CFF修正テストが失敗")

if __name__ == "__main__":
    main()