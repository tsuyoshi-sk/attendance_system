# 🚀 5分クイックスタート

**目標**: とりあえず動かしたい人向けの最短手順

## 前提条件
- Python 3.9以上（3.11推奨）
- Git
- jq（smoke testスクリプト用、オプション）

## 🎯 最短手順（venv版）

### 1. リポジトリのクローン (30秒)
```bash
git clone https://github.com/tsuyoshi-sk/attendance_system.git
cd attendance_system
```

### 2. 仮想環境作成 & 依存関係インストール (2分)
```bash
# venv作成
python3 -m venv .venv

# 有効化（macOS/Linux）
source .venv/bin/activate

# または有効化（Windows）
# .venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

### 3. 環境設定 (1分)
```bash
# 環境変数ファイルをコピー
cp .env.example .env

# データディレクトリ作成
mkdir -p data

# 設定検証（オプション）
python scripts/validate_env.py
```

### 4. データベース初期化 (30秒)
```bash
# データベースとテーブルを作成
python scripts/init_database.py

# または Alembicマイグレーション
alembic upgrade head
```

### 5. サーバー起動 (30秒)
```bash
# 開発サーバー起動（ポート8080）
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 6. 動作確認 (30秒)

#### ブラウザでAPIドキュメントにアクセス
```
http://localhost:8080/docs
```
**✨ Swagger UI が表示されれば成功！**

#### ヘルスチェック
```bash
curl http://localhost:8080/health
```

#### 統合ヘルスチェック
```bash
curl http://localhost:8080/health/integrated
```

## 🧪 自動動作確認（推奨）

すべての基本機能を一度に確認できる smoke test スクリプトを用意しています：

```bash
# サーバーを起動した状態で、別のターミナルで実行
bash scripts/smoke.sh
```

**このスクリプトは以下を自動実行します：**
- ✅ データベース初期化
- ✅ 管理者ユーザー作成（admin / admin123!）
- ✅ ログイン
- ✅ 従業員作成
- ✅ 打刻 4種類（IN / OUTSIDE / RETURN / OUT）
- ✅ 日次レポート取得
- ✅ 月次レポート取得
- ✅ CSV エクスポート

**成功すると、すべてのチェックマーク✓が表示されます。**

## 🔧 トラブルシューティング

### よくあるエラー

#### 1. **ポートが既に使用されている**
```
ERROR: [Errno 48] Address already in use
```
**原因**: ポート8080が既に他のプロセスで使用されている

**解決法**:
```bash
# macOS/Linux: 使用中のプロセスを確認
lsof -i :8080

# プロセスを終了
kill -9 <PID>

# または別のポートを使用
uvicorn backend.app.main:app --port 8081
```

#### 2. **データベースファイルが見つからない**
```
Database file not found: sqlite:///data/attendance.db
```
**原因**: `data/`ディレクトリまたは`attendance.db`が存在しない

**解決法**:
```bash
# dataディレクトリを作成
mkdir -p data

# データベースを初期化
python scripts/init_database.py

# または Alembic
alembic upgrade head
```

#### 3. **認証トークンの有効期限切れ**
```
{"error":{"message":"認証情報を検証できませんでした","status_code":401}}
```
**原因**: JWTトークンの有効期限（デフォルト15分）が切れた

**解決法**:
```bash
# 再度ログインして新しいトークンを取得
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=admin' \
  --data-urlencode 'password=admin123!' | jq -r '.access_token')

# トークンの有効期限を延長したい場合は .env で設定
# JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480  # 8時間
```

#### 4. **データベースのパス勘違い**
```
実際のDBパス: data/attendance.db
勘違い例: ./attendance.db, test.db
```
**確認方法**:
```bash
# .env ファイルを確認
grep DATABASE_URL .env

# 正しい設定
DATABASE_URL=sqlite:///data/attendance.db

# 間違った設定例
DATABASE_URL=sqlite:///attendance.db  # data/ がない
DATABASE_URL=sqlite:///./test.db      # パスが違う
```

#### 5. **ModuleNotFoundError**
```
ModuleNotFoundError: No module named 'backend'
```
**解決法**:
```bash
# PYTHONPATHを設定
export PYTHONPATH=$PWD

# または requirements.txt を再インストール
pip install -r requirements.txt
```

#### 6. **Secret key が短すぎる**
```
Secret key too short (minimum 32 characters required)
```
**解決法**:
```bash
# セキュアなキーを生成
python scripts/validate_env.py

# 表示されたキーを .env の JWT_SECRET_KEY にコピー
# JWT_SECRET_KEY=<generated-key>
```

### PaSoRi使用時

**RC-S380/RC-S300を使う場合**
```bash
# macOSの場合
brew install libusb
pip install nfcpy

# 接続テスト
python -m nfc

# 環境変数設定
export PASORI_DEVICE=auto  # または rcs380, rcs300
```

**モックモード（ハードウェアなし）**
```bash
export PASORI_MOCK_MODE=true
```

## 次のステップ

✅ 動いた！ → [詳細ドキュメント](README.md) を確認  
❌ 動かない → [Issues](https://github.com/tsuyoshi-sk/attendance_system/issues) で質問

---
**所要時間**: 約5分  
**対象**: とりあえず試したい開発者