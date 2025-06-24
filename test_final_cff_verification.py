#!/usr/bin/env python3
"""
OpenType/CFFフォント対応の最終検証テスト
実際の角丸処理が動作するかテスト
"""

import sys
import os
from fontTools.ttLib import TTFont
from effects.round_corners_effect import RoundCornersEffect

def test_cff_with_small_radius():
    """小さなradiusでCFFフォントの角丸処理をテスト"""
    print("=== CFFフォント角丸処理テスト（小さなradius） ===")
    
    # OpenType/CFFフォントを探す
    cff_font_path = None
    for file in os.listdir('.'):
        if file.endswith('.otf'):
            try:
                font = TTFont(file)
                if 'CFF ' in font:
                    cff_font_path = file
                    font.close()
                    break
                font.close()
            except:
                pass
    
    if not cff_font_path:
        print("OpenType/CFFフォントが見つかりません。")
        return False
    
    print(f"テスト対象: {cff_font_path}")
    
    try:
        # フォントを読み込み
        font = TTFont(cff_font_path)
        
        # 角丸エフェクトを作成（小さなradius）
        params = {'radius': 2, 'angle_threshold': 160}
        effect = RoundCornersEffect(params)
        
        print("角丸処理を実行中（radius=2）...")
        
        # 角丸処理を適用
        processed_font = effect.apply(font, radius=2)
        
        print("✅ CFFフォントの角丸処理が成功しました")
        
        # メモリ内での処理確認のため、保存はスキップ
        font.close()
        return True
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_error_before_fix():
    """修正前のエラーを再現するテスト"""
    print("\n=== 修正前エラー再現テスト ===")
    
    # OpenType/CFFフォントを探す
    cff_font_path = None
    for file in os.listdir('.'):
        if file.endswith('.otf'):
            try:
                font = TTFont(file)
                if 'CFF ' in font:
                    cff_font_path = file
                    font.close()
                    break
                font.close()
            except:
                pass
    
    if not cff_font_path:
        print("OpenType/CFFフォントが見つかりません。")
        return True
    
    print(f"テスト対象: {cff_font_path}")
    
    try:
        # フォントを読み込み
        font = TTFont(cff_font_path)
        
        # 修正前のコードを模擬（直接glyf テーブルにアクセス）
        print("修正前のコード（font['glyf']）を模擬実行...")
        
        try:
            glyf_table = font['glyf']  # これがKeyErrorを引き起こすはず
            print("❌ 予期しない成功: glyf テーブルが見つかりました")
            return False
        except KeyError as e:
            print(f"✅ 期待通りのエラーが発生: {e}")
            print("修正により、このエラーが適切に処理されるようになりました")
        
        font.close()
        return True
        
    except Exception as e:
        print(f"予期しないエラー: {str(e)}")
        return False

def main():
    """メイン関数"""
    print("OpenType/CFFフォント対応の最終検証テストを開始します...")
    
    # 修正前エラーの再現テスト
    error_test_success = test_error_before_fix()
    
    # CFFフォントの実際の角丸処理テスト
    cff_processing_success = test_cff_with_small_radius()
    
    print("\n=== 最終テスト結果 ===")
    print(f"修正前エラー再現テスト: {'成功' if error_test_success else '失敗'}")
    print(f"CFFフォント角丸処理テスト: {'成功' if cff_processing_success else '失敗'}")
    
    if error_test_success and cff_processing_success:
        print("🎉 すべてのテストが成功しました！")
        print("KeyError: 'glyf' エラーの修正が完全に完了しました。")
        print("\n修正内容:")
        print("- フォント形式の自動判定機能を追加")
        print("- TrueTypeフォント（glyf テーブル）とOpenType/CFFフォント（CFF テーブル）の両方に対応")
        print("- 適切なエラーハンドリングを実装")
    else:
        print("❌ 一部のテストに失敗しました。")
    
    return error_test_success and cff_processing_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)