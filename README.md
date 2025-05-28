# 勤怠管理システム

[![Tests](https://github.com/tsuyoshi-sk/attendance_system/actions/workflows/test.yml/badge.svg)](https://github.com/tsuyoshi-sk/attendance_system/actions)
[![Code Quality](https://github.com/tsuyoshi-sk/attendance_system/actions/workflows/quality.yml/badge.svg)](https://github.com/tsuyoshi-sk/attendance_system/actions)
[![CI/CD Pipeline](https://github.com/tsuyoshi-sk/attendance_system/actions/workflows/ci.yml/badge.svg)](https://github.com/tsuyoshi-sk/attendance_system/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/tsuyoshi-sk/attendance_system/branch/main/graph/badge.svg)](https://codecov.io/gh/tsuyoshi-sk/attendance_system)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

PaSoRi RC-S300を使用したFeliCaベースの勤怠管理システム

## 概要

このシステムは、ソニーのPaSoRi RC-S300リーダーを使用して、FeliCaカード（Suica、PASMO、社員証など）で従業員の勤怠を管理するシステムです。

### 主な機能

- 🚪 **打刻機能**: 出勤・退勤・外出・戻りの4種類の打刻
- 👥 **従業員管理**: 最大6名の従業員情報管理
- 📊 **レポート機能**: 日次・月次の勤怠レポート自動生成
- 💾 **データ管理**: SQLiteによるローカルデータ保存
- 📡 **オフライン対応**: ネットワーク障害時のローカルキュー機能
- 🔔 **通知機能**: Slack連携による打刻通知
- 📁 **エクスポート**: CSV形式での勤怠データ出力

## 動作環境

- Python 3.8以上
- PaSoRi RC-S300（USB接続）
- 対応OS: Windows 10/11, macOS, Linux

## クイックスタート

### 1. リポジトリのクローン

```bash
git clone https://github.com/tsuyoshi-sk/attendance_system.git
cd attendance_system
```

### 2. 自動セットアップ

```bash
# セットアップスクリプトを実行
bash setup.sh

# または
make setup
```

### 3. 環境設定

`.env.example`を`.env`にコピーして、必要な設定を行います：

```bash
cp config/.env.example .env
```

重要な設定項目：
- `SECRET_KEY`: 本番環境では必ず変更してください
- `IDM_HASH_SECRET`: カードIDのハッシュ化に使用
- `SLACK_WEBHOOK_URL`: Slack通知を使用する場合に設定

### 4. アプリケーション起動

```bash
# 本番モード
make run

# 開発モード（自動リロード）
make dev
```

### 5. APIドキュメント確認

ブラウザで以下にアクセス：
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc

## 使い方

### PaSoRiテスト

```bash
# ハードウェアテストツールを実行
make hardware-test

# または
python hardware/pasori_test.py
```

### 従業員登録

1. APIドキュメント（/docs）にアクセス
2. `/api/v1/admin/employees`で従業員を作成
3. `/api/v1/admin/employees/{id}/card`でカードを登録

### 打刻

カードをPaSoRiにかざすと自動的に打刻されます。

## 開発

### プロジェクト構成

```
attendance_system/
├── backend/          # バックエンドアプリケーション
│   ├── app/         # FastAPIアプリケーション
│   │   ├── api/     # APIエンドポイント
│   │   ├── models/  # データベースモデル
│   │   └── services/# ビジネスロジック
│   └── migrations/  # データベースマイグレーション
├── hardware/        # PaSoRi関連
├── config/          # 設定ファイル
├── tests/           # テストコード
└── docs/            # ドキュメント
```

### 開発コマンド

```bash
# テスト実行
make test

# カバレッジ付きテスト
make test-cov

# コードフォーマット
make format

# リント
make lint

# 型チェック
make check

# セキュリティチェック
make security

# 品質チェック（全チェック実行）
make quality

# CI/CDパイプライン（ローカル実行）
make ci
```

### コーディング規約

- PEP 8準拠
- Black formatterを使用
- 型ヒント推奨
- Docstring必須（Google style）

## API仕様

### 主要エンドポイント

#### 打刻
- `POST /api/v1/punch/` - 打刻記録
- `GET /api/v1/punch/status/{employee_id}` - 打刻状況確認
- `GET /api/v1/punch/history/{employee_id}` - 打刻履歴

#### 管理
- `GET /api/v1/admin/employees` - 従業員一覧
- `POST /api/v1/admin/employees` - 従業員登録
- `POST /api/v1/admin/employees/{id}/card` - カード登録

## トラブルシューティング

### PaSoRiが認識されない

1. USBケーブルの接続確認
2. ドライバのインストール確認
3. 他のアプリケーションがPaSoRiを使用していないか確認

Linux環境の場合：
```bash
# udevルールの設定
sudo cp docs/90-pasori.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

### モックモード

PaSoRiが利用できない環境では、自動的にモックモードで動作します。

```bash
# .envで明示的に設定
PASORI_MOCK_MODE=True
```

## セキュリティ

### 認証・セキュリティ機能

- **JWT認証**: 32文字以上の強力なシークレットキーを強制
- **安全なシリアライゼーション**: pickleの代わりにorjsonを使用
- **環境変数管理**: pydanticによる設定検証
- **セキュリティスキャン**: banditとsafetyによる脆弱性チェック
- **機密ファイル保護**: .gitignoreと.gitattributesで完全保護
- **カードIDハッシュ化**: SHA-256でハッシュ化して保存
- **SQLインジェクション対策**: SQLAlchemy ORM使用

### CI/CDパイプライン

- **自動テスト**: Python 3.9-3.12で並列実行
- **コード品質**: flake8, mypy, black, isortによる自動チェック
- **カバレッジ**: 80%以上のテストカバレッジを強制
- **マルチDB対応**: PostgreSQLとSQLiteでのテスト実行
- **セキュリティ監査**: 定期的な脆弱性スキャン

## ライセンス

MIT License

## 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## サポート

問題や質問がある場合は、[Issues](https://github.com/tsuyoshi-sk/attendance_system/issues)で報告してください。

## 作者

- GitHub: [@tsuyoshi-sk](https://github.com/tsuyoshi-sk)