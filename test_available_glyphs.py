#!/usr/bin/env python3
"""
利用可能なグリフを確認し、実際のOTF/TTF比較テストを実行
"""

import sys
import os
from fontTools.ttLib import TTFont

def list_available_glyphs(font_path, max_glyphs=10):
    """フォント内の利用可能なグリフを一覧表示"""
    print(f"\n=== グリフ一覧: {os.path.basename(font_path)} ===")
    
    try:
        font = TTFont(font_path)
        
        has_glyf = 'glyf' in font
        has_cff = 'CFF ' in font
        
        if has_cff:
            # CFFフォントの場合
            cff_table = font['CFF ']
            cff = cff_table.cff
            topDict = cff.topDictIndex[0]
            charStrings = topDict.CharStrings
            glyph_names = list(charStrings.keys())
            print(f"CFFフォント - 総グリフ数: {len(glyph_names)}")
            
        elif has_glyf:
            # TTFフォントの場合
            glyf_table = font['glyf']
            glyph_names = list(glyf_table.keys())
            print(f"TTFフォント - 総グリフ数: {len(glyph_names)}")
        
        else:
            print("サポートされていないフォント形式")
            return []
        
        # 最初のいくつかのグリフを表示
        print(f"最初の{min(max_glyphs, len(glyph_names))}個のグリフ:")
        for i, name in enumerate(glyph_names[:max_glyphs]):
            print(f"  [{i}] {name}")
        
        # 一般的な文字グリフを探す
        common_glyphs = ['A', 'a', 'B', 'b', 'C', 'c', 'space', 'period', 'comma', 'zero', 'one']
        found_common = []
        
        for glyph in common_glyphs:
            if glyph in glyph_names:
                found_common.append(glyph)
        
        if found_common:
            print(f"一般的なグリフ: {found_common}")
        
        return glyph_names
        
    except Exception as e:
        print(f"エラー: {e}")
        return []

def find_suitable_test_fonts():
    """テストに適したフォントペアを探す"""
    print("テスト用フォントペアを探しています...")
    
    # システムフォントパス
    font_paths = [
        "/System/Library/Fonts/",
        "/Library/Fonts/",
    ]
    
    otf_fonts = []
    ttf_fonts = []
    
    for base_path in font_paths:
        try:
            if os.path.exists(base_path):
                for file in os.listdir(base_path):
                    full_path = os.path.join(base_path, file)
                    if file.lower().endswith('.otf'):
                        otf_fonts.append(full_path)
                    elif file.lower().endswith('.ttf'):
                        ttf_fonts.append(full_path)
        except (OSError, PermissionError):
            continue
    
    print(f"OTFフォント: {len(otf_fonts)}個")
    print(f"TTFフォント: {len(ttf_fonts)}個")
    
    # 各フォントのグリフを確認
    suitable_otf = None
    suitable_ttf = None
    common_glyph = None
    
    # OTFフォントから適切なものを探す
    for otf_path in otf_fonts[:5]:  # 最初の5個をチェック
        try:
            glyphs = list_available_glyphs(otf_path, 5)
            if glyphs:
                # 一般的なグリフがあるかチェック
                test_glyphs = ['A', 'a', 'space', 'period', 'zero']
                for test_glyph in test_glyphs:
                    if test_glyph in glyphs:
                        suitable_otf = otf_path
                        common_glyph = test_glyph
                        break
                if suitable_otf:
                    break
        except Exception as e:
            print(f"OTFフォント読み込みエラー: {os.path.basename(otf_path)} - {e}")
            continue
    
    # TTFフォントから適切なものを探す
    for ttf_path in ttf_fonts[:5]:  # 最初の5個をチェック
        try:
            glyphs = list_available_glyphs(ttf_path, 5)
            if glyphs and common_glyph and common_glyph in glyphs:
                suitable_ttf = ttf_path
                break
        except Exception as e:
            print(f"TTFフォント読み込みエラー: {os.path.basename(ttf_path)} - {e}")
            continue
    
    return suitable_otf, suitable_ttf, common_glyph

def test_specific_glyph_processing(otf_path, ttf_path, glyph_name):
    """特定のグリフでOTF/TTF処理を比較テスト"""
    print(f"\n{'='*60}")
    print(f"詳細比較テスト: グリフ '{glyph_name}'")
    print(f"OTF: {os.path.basename(otf_path)}")
    print(f"TTF: {os.path.basename(ttf_path)}")
    print(f"{'='*60}")
    
    # OTFフォント詳細テスト
    print(f"\n🔍 OTFフォント詳細分析")
    try:
        from test_otf_quality_diagnosis import extract_glyph_paths_cff, convert_recording_to_contours, analyze_coordinate_precision
        
        otf_font = TTFont(otf_path)
        otf_paths = extract_glyph_paths_cff(otf_font, glyph_name)
        
        if otf_paths:
            otf_contours = convert_recording_to_contours(otf_paths)
            analyze_coordinate_precision(otf_contours, "(OTF原始)")
            
            # 座標の詳細分析
            print("\nOTF座標の詳細:")
            for i, contour in enumerate(otf_contours[:2]):  # 最初の2つの輪郭
                print(f"  輪郭{i}: {len(contour['coords'])}点")
                for j, coord in enumerate(contour['coords'][:5]):  # 最初の5点
                    flag = contour['flags'][j]
                    curve_type = "オンカーブ" if flag & 1 else "オフカーブ"
                    print(f"    [{j}] {coord} ({curve_type})")
                if len(contour['coords']) > 5:
                    print(f"    ... (残り{len(contour['coords'])-5}点)")
        else:
            print("OTFグリフパス取得失敗")
            
    except Exception as e:
        print(f"OTFテストエラー: {e}")
    
    # TTFフォント詳細テスト
    print(f"\n🔍 TTFフォント詳細分析")
    try:
        from test_otf_quality_diagnosis import extract_glyph_paths_ttf
        
        ttf_font = TTFont(ttf_path)
        ttf_data = extract_glyph_paths_ttf(ttf_font, glyph_name)
        
        if ttf_data:
            # TTF座標の詳細分析
            coords = ttf_data['coords']
            flags = ttf_data['flags']
            
            print("\nTTF座標の詳細:")
            for i, coord in enumerate(coords[:10]):  # 最初の10点
                flag = flags[i] if i < len(flags) else 0
                curve_type = "オンカーブ" if flag & 1 else "オフカーブ"
                print(f"  [{i}] {coord} ({curve_type})")
            if len(coords) > 10:
                print(f"  ... (残り{len(coords)-10}点)")
        else:
            print("TTFグリフパス取得失敗")
            
    except Exception as e:
        print(f"TTFテストエラー: {e}")

def main():
    """メイン処理"""
    print("フォントグリフ分析 & 比較テスト")
    print("=" * 50)
    
    # 適切なテストフォントを探す
    otf_path, ttf_path, common_glyph = find_suitable_test_fonts()
    
    if otf_path and ttf_path and common_glyph:
        print(f"\n✅ テスト用フォントペアが見つかりました:")
        print(f"OTF: {os.path.basename(otf_path)}")
        print(f"TTF: {os.path.basename(ttf_path)}")
        print(f"テストグリフ: '{common_glyph}'")
        
        # 詳細比較テスト実行
        test_specific_glyph_processing(otf_path, ttf_path, common_glyph)
        
    else:
        print("\n❌ 適切なテストフォントペアが見つかりませんでした")
        
        # 利用可能なフォントの詳細を表示
        if otf_path:
            print(f"\nOTFフォントは利用可能: {os.path.basename(otf_path)}")
            list_available_glyphs(otf_path, 10)
        
        if ttf_path:
            print(f"\nTTFフォントは利用可能: {os.path.basename(ttf_path)}")
            list_available_glyphs(ttf_path, 10)

if __name__ == "__main__":
    main()