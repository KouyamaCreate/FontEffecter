#!/usr/bin/env python3
"""
nominalWidthXエラーを再現するテストスクリプト
"""

import sys
import os

def test_round_corners_effect():
    """角丸処理を実行してエラーを再現"""
    try:
        from fontTools.ttLib import TTFont
        from effects.round_corners_effect import RoundCornersEffect
        
        print("=== nominalWidthXエラー再現テスト ===")
        
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
        font = TTFont(font_path)
        
        # 角丸エフェクトを作成
        params = {'radius': 10, 'angle_threshold': 160}
        effect = RoundCornersEffect(params)
        
        print("角丸処理を開始...")
        
        # 角丸処理を実行（エラーが発生する可能性がある）
        try:
            result_font = effect.apply(font, radius=10)
            print("角丸処理が正常に完了しました")
            return True
        except AttributeError as e:
            if "nominalWidthX" in str(e):
                print(f"nominalWidthXエラーが発生しました: {e}")
                
                # エラーの詳細を調査
                import traceback
                print("\n=== エラーの詳細 ===")
                traceback.print_exc()
                
                # エラーが発生した場所を特定
                print("\n=== エラー発生箇所の調査 ===")
                return False
            else:
                print(f"別のAttributeErrorが発生: {e}")
                import traceback
                traceback.print_exc()
                return False
        except Exception as e:
            print(f"予期しないエラーが発生: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_different_fonts():
    """異なるフォントでテストを実行"""
    test_fonts = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Times.ttc",
        "/System/Library/Fonts/Courier.ttc",
        "/System/Library/Fonts/Arial.ttf"
    ]
    
    for font_path in test_fonts:
        if os.path.exists(font_path):
            print(f"\n=== {font_path} でのテスト ===")
            try:
                from fontTools.ttLib import TTFont
                font = TTFont(font_path)
                
                # フォント形式を確認
                has_cff = 'CFF ' in font
                has_glyf = 'glyf' in font
                
                print(f"CFF: {has_cff}, glyf: {has_glyf}")
                
                if has_cff:
                    print("CFFフォントで角丸処理をテスト...")
                    from effects.round_corners_effect import RoundCornersEffect
                    params = {'radius': 5, 'angle_threshold': 160}
                    effect = RoundCornersEffect(params)
                    
                    try:
                        result_font = effect.apply(font, radius=5)
                        print("✓ 正常に完了")
                    except AttributeError as e:
                        if "nominalWidthX" in str(e):
                            print(f"✗ nominalWidthXエラー発生: {e}")
                            return font_path, e
                        else:
                            print(f"✗ 別のAttributeError: {e}")
                    except Exception as e:
                        print(f"✗ その他のエラー: {e}")
                else:
                    print("CFFフォントではないためスキップ")
                    
            except Exception as e:
                print(f"フォント読み込みエラー: {e}")
    
    return None, None

def main():
    print("nominalWidthXエラーの再現テストを開始...")
    
    # 基本テスト
    success = test_round_corners_effect()
    
    if success:
        print("\n基本テストでエラーが再現されませんでした")
        print("異なるフォントでテストを実行...")
        
        error_font, error = test_with_different_fonts()
        if error_font:
            print(f"\nエラーが再現されました: {error_font}")
            print(f"エラー: {error}")
        else:
            print("\n異なるフォントでもエラーが再現されませんでした")
    
    print("\nテスト完了")

if __name__ == "__main__":
    main()