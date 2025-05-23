# 人数カウンターウェブアプリケーション

AIカメラ（IMX500）を搭載したRaspberry Pi 5用のローカルウェブアプリケーションで、ラインを横切る人の数をカウントし、結果を可視化します。

[English README](README.md)

## 機能

- バウンディングボックスによる人物検出のリアルタイム可視化
- 高度なヒューリスティックを使用したフレーム間の人物追跡
- ライン横断検出とカウント
- 人数カウントの時系列グラフ
- 調整可能な設定（閾値、更新頻度など）
- 検出の隙間を処理できる堅牢な追跡

## 前提条件

- Raspberry Pi 4/5 (他のモデルではテストしていません)
- Raspberry Pi AIカメラ（IMX500）
- IMX500にデプロイされた人物検出用のオブジェクト検出モデル
- Python 3.9以上
- [公式ドキュメント](https://www.raspberrypi.com/documentation/accessories/ai-camera.html)に従ってIMX500 AIカメラのセットアップが完了していること
  - これには`sudo apt install imx500-all`でのパッケージインストールとデモアプリケーションが正常に動作することの確認を含みます

## インストール

1. このリポジトリをRaspberry Piにクローンします：

```bash
git clone https://github.com/TechMind428/AIcam_count.git
cd AIcam_count
```

2. インストールスクリプトを実行します：

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh

# インストールを完了するためには仮想環境の利用が求められる場合があります
例) 
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
```

## ディレクトリ構造

```
AIcam_count/
├── app.py                 # メインアプリケーションのエントリーポイント
├── output_meta.py         # カメラの出力するメタデータをファイル保存するアプリケーション
├── modules/
│   ├── file_monitor.py    # JSONファイルモニタリング
│   ├── person_tracker.py  # 人物追跡アルゴリズム
│   └── line_counter.py    # ライン横断検出
├── static/
│   ├── css/
│   │   └── style.css      # アプリケーションのスタイル
│   └── js/
│       └── main.js        # フロントエンド機能
└── templates/
    └── index.html         # メインアプリケーションページ
```

## 使用方法

1. オブジェクト検出モデルをIMX500カメラにデプロイし、JSONファイルを`/home/temp`に出力する別のプロセスが実行されていることを確認します。

2. Webアプリケーションを起動します：

```bash
source .venv/bin/activate # venvを使用する場合 | venvディレクトリを環境に合わせて変更
python output_meta.py # 別のターミナルを開く必要があるかもしれません
python app.py
```

3. Webブラウザを開き、以下のURLにアクセスします：
   - `http://localhost:8080`（Raspberry Piから直接アクセスする場合）
   - `http://{raspberry-piのIP}:8080`（同じネットワーク上の別のデバイスからアクセスする場合）

## 設定

Webインターフェイスで以下の設定を調整できます：

- **更新頻度**：UIが更新される頻度（ミリ秒単位）
- **信頼度閾値**：検出が有効と見なされるための最小信頼度スコア
- **カウントリセット**：人数カウンターをリセットするボタン

## 技術的実装の詳細

### 人物追跡

アプリケーションは以下を使用してフレーム間で人物を追跡します：

- バウンディングボックスの中心間の距離
- バウンディングボックスのIoU（Intersection over Union）
- バウンディングボックスのサイズの類似性
- 移動軌跡と速度の推定

このアプローチにより、時折検出にギャップがあっても人物のアイデンティティを維持できます。

### ライン横断検出

垂直線はx=320（640x480フレームの中央）に配置されています。アプリケーションは：

- 人物の中心が左から右に横切るタイミングを追跡
- 一方向のカウントを確保（Uターンを無視）
- 信頼度が閾値を超えている場合のみカウント

### JSONファイルモニタリング

アプリケーションは指定されたディレクトリ内の新しいJSONファイルを監視し、それらが表示されると処理します。予想されるJSON形式は次のとおりです：

```json
{
    "time": "20250303145302409",
    "detections": [
        {
            "label": "person",
            "confidence": 0.77734375,
            "left": 625.0,
            "top": 0.0,
            "right": 44.0,
            "bottom": 470.0
        },
        ...
    ]
}
```

## ライセンス

[MITライセンス](LICENSE)
