#!/usr/bin/env python3
"""
CFFフォントのPrivateDict問題を診断するテストスクリプト
"""

import sys
import os

def diagnose_cff_privatedict(font_path):
    """CFFフォントのPrivateDictの状態を詳細に診断"""
    try:
        from fontTools.ttLib import TTFont
        
        print(f"=== CFF PrivateDict 診断: {font_path} ===")
        
        # フォントを読み込み
        font = TTFont(font_path)
        
        # フォント形式の確認
        has_cff = 'CFF ' in font
        has_cff2 = 'CFF2' in font
        
        print(f"CFFテーブル存在: {has_cff}")
        print(f"CFF2テーブル存在: {has_cff2}")
        
        if not has_cff and not has_cff2:
            print("エラー: CFFテーブルが見つかりません")
            return False
        
        # CFFテーブルの詳細分析
        if has_cff:
            print("\n--- CFF テーブル分析 ---")
            cff_table = font['CFF ']
            cff = cff_table.cff
            
            print(f"CFFオブジェクト: {cff}")
            print(f"topDictIndex長さ: {len(cff.topDictIndex)}")
            
            for i, topDict in enumerate(cff.topDictIndex):
                print(f"\n--- TopDict[{i}] ---")
                print(f"TopDict: {topDict}")
                
                # CharStringsの確認
                if hasattr(topDict, 'CharStrings'):
                    charStrings = topDict.CharStrings
                    print(f"CharStrings: {charStrings}")
                    print(f"CharStrings keys数: {len(charStrings.keys())}")
                    
                    # 最初のいくつかのグリフを確認
                    glyph_names = list(charStrings.keys())[:5]
                    for glyph_name in glyph_names:
                        print(f"\n  グリフ '{glyph_name}' の分析:")
                        try:
                            charString = charStrings[glyph_name]
                            print(f"    CharString: {charString}")
                            print(f"    CharString type: {type(charString)}")
                            
                            # PrivateDictの確認
                            if hasattr(charString, 'private'):
                                private = charString.private
                                print(f"    private属性: {private}")
                                print(f"    private type: {type(private)}")
                                
                                if private is not None:
                                    print(f"    private keys: {list(private.keys()) if hasattr(private, 'keys') else 'No keys method'}")
                                    
                                    # nominalWidthXの確認
                                    if hasattr(private, 'nominalWidthX'):
                                        print(f"    nominalWidthX: {private.nominalWidthX}")
                                    else:
                                        print(f"    nominalWidthX属性なし")
                                        
                                    # その他の属性確認
                                    for attr in ['defaultWidthX', 'nominalWidthX', 'Subrs']:
                                        if hasattr(private, attr):
                                            value = getattr(private, attr)
                                            print(f"    {attr}: {value}")
                                else:
                                    print(f"    private is None!")
                            else:
                                print(f"    private属性なし")
                                
                        except Exception as e:
                            print(f"    エラー: {e}")
                            import traceback
                            traceback.print_exc()
                
                # TopDictのPrivate情報確認
                if hasattr(topDict, 'Private'):
                    print(f"\nTopDict.Private: {topDict.Private}")
                    if topDict.Private is not None:
                        print(f"TopDict.Private keys: {list(topDict.Private.keys()) if hasattr(topDict.Private, 'keys') else 'No keys method'}")
                        
                        # nominalWidthXの確認
                        if hasattr(topDict.Private, 'nominalWidthX'):
                            print(f"TopDict.Private.nominalWidthX: {topDict.Private.nominalWidthX}")
                        else:
                            print(f"TopDict.Private.nominalWidthX属性なし")
                    else:
                        print(f"TopDict.Private is None!")
                else:
                    print(f"TopDict.Private属性なし")
        
        return True
        
    except Exception as e:
        print(f"診断中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # テスト用のCFFフォントファイルを探す
    test_fonts = [
        "output_rounded.otf",  # 既存の出力ファイル
        "/System/Library/Fonts/Helvetica.ttc",  # macOSのシステムフォント
        "/System/Library/Fonts/Times.ttc",
        "/System/Library/Fonts/Courier.ttc"
    ]
    
    found_font = None
    for font_path in test_fonts:
        if os.path.exists(font_path):
            found_font = font_path
            break
    
    if found_font:
        print(f"テストフォント: {found_font}")
        diagnose_cff_privatedict(found_font)
    else:
        print("テスト用のフォントファイルが見つかりません")
        print("利用可能なフォントファイルを指定してください:")
        print("python test_cff_privatedict_diagnosis.py <font_path>")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        font_path = sys.argv[1]
        if os.path.exists(font_path):
            diagnose_cff_privatedict(font_path)
        else:
            print(f"フォントファイルが見つかりません: {font_path}")
    else:
        main()