# Imagen 3 Image Generation App

Google Cloud Platform の Imagen 3 APIを使用して画像を生成するPythonアプリケーション。

## セットアップ

1. 必要な環境
- Python 3.9以上
- Google Cloud Platformアカウント
- Imagen APIへのアクセス権限

2. 環境構築

bash
仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate # MacOS/Linux
または .venv\Scripts\activate # Windows
依存パッケージのインストール
pip install -r requirements.txt


3. GCP認証の設定
- GCPコンソールから認証情報（サービスアカウントキー）をダウンロード
- `credentials/credentials.json`として保存
- 環境変数の設定
  ```bash
  cp .env.sample .env
  # .envファイルを編集して適切な値を設定
  ```

4. 実行
bash
python draw.py


## 使用方法

1. プロンプトの入力
- 1行または複数行のプロンプトを入力
- 複数行の場合は、空行を2回入力して次のプロンプトへ
- 入力完了時は'done'を入力

2. 画像生成
- 各プロンプトに対して1-4枚の画像を生成可能
- 生成された画像は`images/[session_id]`に保存
- メタデータは`metadata.json`として保存

## ライセンス

MIT License

# GCPプロジェクトの設定
gcloud config set project your-project-id

# Vertex AI APIの有効化
gcloud services enable aiplatform.googleapis.com

# サービスアカウントの作成（必要な場合）
gcloud iam service-accounts create imagen-app \
    --display-name="Imagen App Service Account"

# 権限の付与
gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:imagen-app@your-project-id.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# 認証情報のダウンロード
gcloud iam service-accounts keys create credentials/credentials.json \
    --iam-account=imagen-app@your-project-id.iam.gserviceaccount.com

#ディレクトリー構造
imagen3_app/
├── .env.sample
├── .gitignore
├── .venv/
├── README.md
├── credentials/
│   └── .gitkeep
├── draw.py
├── images/
│   └── .gitkeep
└── requirements.txt    