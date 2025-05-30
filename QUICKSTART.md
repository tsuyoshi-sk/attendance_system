# 🚀 5分クイックスタート

**目標**: とりあえず動かしたい人向けの最短手順

## 前提条件
- Python 3.9以上
- Git

## 手順

### 1. クローン (30秒)
```bash
git clone https://github.com/tsuyoshi-sk/attendance_system.git
cd attendance_system
```

### 2. 環境設定 (1分)
```bash
# 環境変数コピー
cp .env.example .env

# 設定検証（オプション）
python scripts/validate_env.py
```

### 3. 依存関係インストール (2分)
```bash
# Poetry使用（推奨）
pip install poetry
poetry install

# または pip使用
pip install -r requirements.txt
```

### 4. データベース初期化 (30秒)
```bash
python scripts/init_database.py
```

### 5. 起動 (30秒)
```bash
# Poetry使用
poetry run uvicorn backend.app.main:app --reload

# または直接実行
uvicorn backend.app.main:app --reload
```

### 6. 確認 (30秒)
ブラウザで http://localhost:8000 を開く

## トラブルシューティング

### よくあるエラー

**1. `ModuleNotFoundError`**
```bash
# 解決法
export PYTHONPATH=$PWD
```

**2. `Database not found`**
```bash
# 解決法
python scripts/init_database.py
```

**3. `Secret key too short`**
```bash
# 解決法
python scripts/validate_env.py
# 表示されたキーを .env にコピー
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