# FontEffecter

## 概要
FontEffecterは、OTF/TTFフォントファイルに様々なエフェクト（例：角丸加工など）を適用できるPythonスクリプトです。エフェクト内容や入出力ファイルは設定ファイル（config.yaml）で柔軟に指定できます。

## インストール

以下のコマンドで必要な依存ライブラリをインストールしてください。

```sh
pip install -r requirements.txt
```

## 使い方

1. **設定ファイル（config.yaml）の編集**

   - 入力フォントファイルのパス、出力先ファイルのパス、適用したいエフェクトを`config.yaml`で設定します。
   - Variable Fontを利用する場合は、`variation`セクションで各軸（例：`wght`, `wdth`など）の値を指定できます。
   - 例：
     ```yaml
     input_font: ./input/font.otf
     output_font: ./output/font_rounded.otf
     effects:
       - name: round_corners
         params:
           radius: 10                # 角を丸める半径（単位：フォント単位）
           angle_threshold: 30       # 角度しきい値（単位：度）
 
       # Variable Fontのvariation指定例
       variation:
         wght: 700    # Weight軸を700に指定
         wdth: 100    # Width軸を100に指定
       ```
     - `params` で指定できるパラメータ:
         - `radius`: 角を丸める半径（単位：フォント単位）。
         - `angle_threshold`: どのくらい鋭い角を丸めるかを制御する設定値（単位：度）。値が小さいほど、より鋭い角のみが丸め処理の対象になります。
     - `variation`セクションを指定することで、Variable Fontの特定インスタンス（例：太さwght=700、幅wdth=100など）を生成できます。利用可能な軸名や値の範囲は各フォントによって異なります。

2. **スクリプトの実行**

   - 以下のコマンドでエフェクトを適用します。
     ```sh
     python font_processor.py
     ```

   - スクリプトは`config.yaml`の内容に従って処理を行い、指定した出力先にエフェクト適用済みのフォントファイルを生成します。

3. **GUIアプリケーションの利用**

   - 以下のコマンドでGUIアプリケーションを起動できます。
     ```sh
     python gui.py
     ```
   - GUIでは、設定内容の表示・編集、ファイル選択、エフェクトパラメータの変更、設定の保存、そしてフォント処理の実行を、グラフィカルな操作で行うことができます。
   - `round_corners` エフェクトを選択した場合、「角度しきい値（angle_threshold）」の入力フィールドが追加され、どの程度鋭い角を丸めるかをGUI上で指定できます。
   - Variable Fontを読み込んだ場合、利用可能なバリエーション軸（例：wght, wdthなど）が自動で一覧表示され、各軸ごとにスライダーや数値入力で値を自由に設定できます。設定した値は`variation`セクションとして自動的に反映されます。
---

### ファイル構成例

- [`font_processor.py`](font_processor.py:1): メインスクリプト
- [`config.yaml`](config.yaml:1): 設定ファイル
- [`requirements.txt`](requirements.txt:1): 依存ライブラリ一覧
- `effects/`: エフェクト定義用Pythonモジュール群

---

## ライセンス

本プロジェクトはMITライセンスの下で公開されています。