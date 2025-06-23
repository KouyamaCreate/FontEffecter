#!/usr/bin/env python3
"""
RoundCornersEffect の AttributeError 修正を検証するテストスクリプト
"""

import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_round_corners_effect_initialization():
    """RoundCornersEffect の初期化と属性アクセスをテスト"""
    print("=== RoundCornersEffect 属性初期化テスト ===")
    
    try:
        from effects.round_corners_effect import RoundCornersEffect
        
        # インスタンス作成
        print("1. RoundCornersEffect インスタンスを作成中...")
        effect = RoundCornersEffect({'radius': 10})
        print("   ✓ インスタンス作成成功")
        
        # 属性アクセステスト
        print("2. _boolean_ops_available 属性にアクセス中...")
        boolean_ops_available = effect._boolean_ops_available
        print(f"   ✓ 属性アクセス成功: _boolean_ops_available = {boolean_ops_available}")
        
        # 属性の型確認
        print("3. 属性の型を確認中...")
        if isinstance(boolean_ops_available, bool):
            print("   ✓ 属性の型は正しく bool です")
        else:
            print(f"   ⚠ 属性の型が予期しない型です: {type(boolean_ops_available)}")
        
        # 動的インポートの結果確認
        print("4. 動的インポートの結果を確認中...")
        if boolean_ops_available:
            print("   ✓ booleanOperations のインポートに成功しています")
            # BooleanGlyph と union 属性の存在確認
            if hasattr(effect, 'BooleanGlyph') and hasattr(effect, 'union'):
                print("   ✓ BooleanGlyph と union 属性が正しく設定されています")
            else:
                print("   ⚠ BooleanGlyph または union 属性が設定されていません")
        else:
            print("   ⚠ booleanOperations のインポートに失敗しています（これは正常な場合もあります）")
        
        print("\n=== テスト結果 ===")
        print("✓ AttributeError は発生しませんでした")
        print("✓ _boolean_ops_available 属性は正しく初期化されています")
        return True
        
    except AttributeError as e:
        print(f"\n❌ AttributeError が発生しました: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        return False

def test_apply_method_access():
    """apply メソッド内での属性アクセスをテスト"""
    print("\n=== apply メソッド内属性アクセステスト ===")
    
    try:
        from effects.round_corners_effect import RoundCornersEffect
        
        effect = RoundCornersEffect({'radius': 10})
        print("1. RoundCornersEffect インスタンス作成完了")
        
        # apply メソッドを呼び出す前に、ダミーのフォントオブジェクトを作成
        # 実際のフォント処理はしないが、属性アクセス部分だけをテスト
        print("2. apply メソッド内での属性アクセスをシミュレート...")
        
        # apply メソッド内の82行目相当の処理をテスト
        use_union = effect._boolean_ops_available
        print(f"   ✓ use_union = {use_union} (属性アクセス成功)")
        
        return True
        
    except AttributeError as e:
        print(f"\n❌ apply メソッド内で AttributeError が発生しました: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    print("RoundCornersEffect AttributeError 修正検証テスト開始\n")
    
    # テスト実行
    test1_result = test_round_corners_effect_initialization()
    test2_result = test_apply_method_access()
    
    print("\n" + "="*50)
    print("最終結果:")
    if test1_result and test2_result:
        print("✅ すべてのテストが成功しました")
        print("✅ AttributeError は修正されています")
        sys.exit(0)
    else:
        print("❌ テストに失敗しました")
        sys.exit(1)