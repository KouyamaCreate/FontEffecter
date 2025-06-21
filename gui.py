import tkinter as tk
from tkinter import filedialog, messagebox
import yaml
import os
from font_processor import FontProcessor
from fontTools.ttLib import TTFont

CONFIG_PATH = "config.yaml"

class FontConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("フォント設定エディタ")
        self.config = {}
        self.create_widgets()
        self.load_config()

    def create_widgets(self):
        # 入力フォント
        tk.Label(self.root, text="入力フォントファイル:").grid(row=0, column=0, sticky="e")
        self.input_entry = tk.Entry(self.root, width=40)
        self.input_entry.grid(row=0, column=1)
        tk.Button(self.root, text="参照...", command=self.browse_input).grid(row=0, column=2)

        # 出力フォント
        tk.Label(self.root, text="出力フォントファイル:").grid(row=1, column=0, sticky="e")
        self.output_entry = tk.Entry(self.root, width=40)
        self.output_entry.grid(row=1, column=1)
        tk.Button(self.root, text="参照...", command=self.browse_output).grid(row=1, column=2)

        # round_corners/radius
        tk.Label(self.root, text="角丸半径 (radius):").grid(row=2, column=0, sticky="e")
        self.radius_var = tk.StringVar()
        self.radius_entry = tk.Entry(self.root, textvariable=self.radius_var, width=10)
        self.radius_entry.grid(row=2, column=1, sticky="w")

        # 角度しきい値 (angle_threshold)
        tk.Label(self.root, text="角度しきい値 (angle threshold):").grid(row=3, column=0, sticky="e")
        self.angle_threshold_var = tk.StringVar()
        self.angle_threshold_entry = tk.Entry(self.root, textvariable=self.angle_threshold_var, width=10)
        self.angle_threshold_entry.grid(row=3, column=1, sticky="w")

        # 直線判定の許容誤差

        # variationセクション（動的）
        self.variation_frame = tk.LabelFrame(self.root, text="Variable Font: variation設定（軸名と値）")
        self.variation_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        self.variation_vars = {}  # 軸名→StringVar

        # ボタン
        tk.Button(self.root, text="設定を保存", command=self.save_config).grid(row=6, column=0, pady=15)
        tk.Button(self.root, text="処理実行", command=self.run_processing).grid(row=6, column=1, pady=15)
        tk.Button(self.root, text="終了", command=self.root.quit).grid(row=6, column=2, pady=15)

    def setup_variation_fields(self, font_path=None, variation_dict=None):
        # 現在のフィールドをクリア
        for widget in self.variation_frame.winfo_children():
            widget.destroy()
        self.variation_vars = {}

        axes = []
        if font_path and os.path.exists(font_path):
            try:
                font = TTFont(font_path)
                if "fvar" in font:
                    axes = font["fvar"].axes
            except Exception as e:
                axes = []
        if axes:
            for idx, axis in enumerate(axes):
                tag = axis.axisTag
                min_v, default_v, max_v = axis.minValue, axis.defaultValue, axis.maxValue
                tk.Label(self.variation_frame, text=f"{tag} ({min_v}-{max_v})").grid(row=idx, column=0, sticky="e")
                var = tk.StringVar()
                val = ""
                if variation_dict and tag in variation_dict:
                    val = str(variation_dict[tag])
                else:
                    val = str(int(default_v) if default_v.is_integer() else default_v)
                var.set(val)
                entry = tk.Entry(self.variation_frame, textvariable=var, width=10)
                entry.grid(row=idx, column=1, sticky="w")
                self.variation_vars[tag] = var
        else:
            tk.Label(self.variation_frame, text="（Variable Fontでない場合は何も表示されません）").grid(row=0, column=0, sticky="w")

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            messagebox.showerror("エラー", f"{CONFIG_PATH} が見つかりません。")
            return
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, self.config.get("input_font", ""))
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, self.config.get("output_font", ""))
        # round_cornersエフェクトのradius取得
        radius = ""
        effects = self.config.get("effects", [])
        for eff in effects:
            if eff.get("name") == "round_corners":
                radius = eff.get("params", {}).get("radius", "")
                angle_threshold = eff.get("params", {}).get("angle_threshold", "")
            self.radius_var.set(str(radius))
            self.angle_threshold_var.set(str(angle_threshold))

        # variation欄のセットアップ
        variation_dict = self.config.get("variation", None)
        input_font_path = self.input_entry.get()
        self.setup_variation_fields(font_path=input_font_path, variation_dict=variation_dict)

    def browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("Font files", "*.ttf *.otf"), ("All files", "*.*")])
        if path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, path)
            # variation欄を再セットアップ
            self.setup_variation_fields(font_path=path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".otf", filetypes=[("Font files", "*.otf *.ttf"), ("All files", "*.*")])
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)

    def save_config(self):
        # 現在のGUI値をconfig dictに反映
        self.config["input_font"] = self.input_entry.get()
        self.config["output_font"] = self.output_entry.get()
        # effects更新
        radius = self.radius_var.get()
        updated = False
        for eff in self.config.get("effects", []):
            if eff.get("name") == "round_corners":
                eff.setdefault("params", {})["radius"] = int(radius) if radius else 0
                # angle_thresholdも保存
                angle_threshold = self.angle_threshold_var.get()
                eff["params"]["angle_threshold"] = int(angle_threshold) if angle_threshold else 160
                updated = True
        if not updated:
            # round_cornersがなければ追加
            self.config.setdefault("effects", []).append({
                "name": "round_corners",
                "params": {
                    "radius": int(radius) if radius else 0,
                    "angle_threshold": int(self.angle_threshold_var.get()) if self.angle_threshold_var.get() else 160
                }
            })

        # variation欄をconfigに反映
        if self.variation_vars:
            variation_dict = {}
            for tag, var in self.variation_vars.items():
                val = var.get()
                try:
                    val = float(val)
                except Exception:
                    val = 0
                variation_dict[tag] = val
            self.config["variation"] = variation_dict if variation_dict else None
        else:
            self.config["variation"] = None

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f, allow_unicode=True)
        messagebox.showinfo("保存", "設定を保存しました。")

    def run_processing(self):
        # まず保存
        self.save_config()
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            processor = FontProcessor.from_config_dict(cfg)
            processor.run()
            messagebox.showinfo("完了", f"処理が完了しました。\n出力ファイル: {self.output_entry.get()}")
        except Exception as e:
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FontConfigGUI(root)
    root.mainloop()