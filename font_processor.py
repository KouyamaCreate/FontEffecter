"""
font_processor.py

フォントエフェクトシステムのコアエンジン。
設計詳細は DESIGN.md を参照。
"""

import yaml
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
import importlib
import os

class FontProcessor:
    def __init__(self, config_path=None, config_dict=None):
        if config_dict is not None:
            self.config = config_dict
        elif config_path is not None:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        else:
            raise ValueError("Either config_path or config_dict must be provided")
        self.input_font = self.config["input_font"]
        self.output_font = self.config["output_font"]
        self.effects = self.config.get("effects", [])

    @classmethod
    def from_config_dict(cls, config_dict):
        return cls(config_dict=config_dict)

    def load_font(self):
        font = TTFont(self.input_font)
        # Variable Font判定
        if "fvar" in font:
            variation = self.config.get("variation", None)
            if variation:
                # variation指定あり→静的インスタンス生成
                var_dict = {k: float(v) for k, v in variation.items()}
                font = instancer.instantiateVariableFont(font, var_dict)
                print(f"Variable Font: variation {var_dict} で静的インスタンス化")
            else:
                print("Variable Font: variation指定なし（デフォルトインスタンスで処理）")
        else:
            print("Static Fontとして処理")
        return font

    def save_font(self, font):
        font.save(self.output_font)

    def apply_effects(self, font):
        for effect in self.effects:
            name = effect["name"]
            params = effect.get("params", {})
            print(f"DEBUG: エフェクト '{name}' の設定パラメータ: {params}")
            module_path = f"effects.{name}_effect"
            class_name = "".join([part.capitalize() for part in name.split("_")]) + "Effect"
            try:
                module = importlib.import_module(module_path)
                effect_class = getattr(module, class_name)
                print(f"DEBUG: エフェクトクラス {class_name} をロードしました")
                # 修正: パラメータを渡してインスタンス作成
                effect_instance = effect_class(params=params)
                print(f"DEBUG: エフェクトインスタンス作成完了（パラメータ付き）")
                print(f"DEBUG: インスタンスにparams属性があるか: {hasattr(effect_instance, 'params')}")
                if hasattr(effect_instance, 'params'):
                    print(f"DEBUG: 現在のparams値: {effect_instance.params}")
                font = effect_instance.apply(font, **params)
                print(f"Applied effect: {name}")
            except Exception as e:
                print(f"Error applying effect '{name}': {e}")
                import traceback
                traceback.print_exc()
        return font

    def run(self):
        font = self.load_font()
        font = self.apply_effects(font)
        self.save_font(font)
        print(f"Output saved to: {self.output_font}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python font_processor.py config.yaml")
        exit(1)
    processor = FontProcessor(sys.argv[1])
    processor.run()