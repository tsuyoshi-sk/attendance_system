# 勤怠管理システム v2.0 🚀

[![Tests](https://github.com/tsuyoshi-sk/attendance_system/actions/workflows/test.yml/badge.svg)](https://github.com/tsuyoshi-sk/attendance_system/actions)
[![Code Quality](https://github.com/tsuyoshi-sk/attendance_system/actions/workflows/quality.yml/badge.svg)](https://github.com/tsuyoshi-sk/attendance_system/actions)
[![Deploy](https://github.com/tsuyoshi-sk/attendance_system/actions/workflows/deploy.yml/badge.svg)](https://github.com/tsuyoshi-sk/attendance_system/actions)
[![codecov](https://codecov.io/gh/tsuyoshi-sk/attendance_system/branch/main/graph/badge.svg)](https://codecov.io/gh/tsuyoshi-sk/attendance_system)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**世界最高レベルのエンタープライズ級iPhone Suica対応勤怠管理システム**

PaSoRi RC-S380、iPhone Suica、Android NFC対応の次世代勤怠管理システム

## 🚀 v2.0 新機能

### 🔥 主要機能
- 🚪 **多様な打刻方式**: PaSoRi・iPhone Suica・Android NFC・QRコード対応
- 👥 **無制限従業員管理**: 6名制限撤廃、エンタープライズ対応
- 🏢 **部署・チーム管理**: 階層的組織管理
- 🔐 **本格認証システム**: JWT・管理者・マネージャー・従業員権限
- 📊 **高度分析機能**: リアルタイム分析・予測機能
- 🌐 **マルチテナント基盤**: 複数組織対応準備済み

### ⚡ エンタープライズ機能
- 🏗️ **Clean Architecture**: ドメイン駆動設計
- 📈 **スケーラビリティ**: 数千名規模対応
- 🔒 **最高セキュリティ**: 64文字JWT・監査ログ
- 🚀 **自動CI/CD**: ステージング→本番デプロイ
- 📱 **PWA対応**: オフライン動作可能
- 🔍 **包括的監視**: パフォーマンス・セキュリティ監視

## 📊 システム完成度

| 項目 | v1.0 | v2.0 |
|------|------|------|
| セキュリティ | ★★★☆☆ | ★★★★★ |
| スケーラビリティ | ★★☆☆☆ | ★★★★★ |
| 運用性 | ★★★☆☆ | ★★★★★ |
| 拡張性 | ★★☆☆☆ | ★★★★★ |
| 企業適用性 | ★★★☆☆ | ★★★★★ |

## 🔒 セキュリティ

### 認証・セキュリティ機能
- **JWT認証**: 64文字以上の強力なシークレットキーを強制
- **安全なシリアライゼーション**: pickleの代わりにorjsonを使用
- **環境変数管理**: pydanticによる設定検証
- **セキュリティスキャン**: banditとsafetyによる脆弱性チェック
- **機密ファイル保護**: .gitignoreと.gitattributesで完全保護
- **カードIDハッシュ化**: SHA-256でハッシュ化して保存
- **SQL インジェクション対策**: SQLAlchemy ORM使用
- **セキュリティヘッダー**: XSS、CSRF、clickjacking対策
- **監査ログ**: 認証・操作・データアクセスの完全追跡

### CI/CDパイプライン
- **自動テスト**: Python 3.9-3.12で並列実行
- **コード品質**: flake8, mypy, black, isortによる自動チェック
- **カバレッジ**: 80%以上のテストカバレッジを強制
- **マルチDB対応**: PostgreSQLとSQLiteでのテスト実行
- **セキュリティ監査**: 定期的な脆弱性スキャン
- **自動デプロイ**: ステージング→本番の自動化

## 🏗️ アーキテクチャ

### Clean Architecture採用
```
attendance_system/
├── backend/
│   ├── domain/           # ドメイン層（ビジネスロジック）
│   ├── usecase/          # ユースケース層（アプリケーション）
│   ├── app/              # インフラ層（API・DB・外部連携）
│   └── auth/             # 認証・認可システム
├── pwa/                  # Progressive Web App
├── hardware/             # ハードウェア制御
└── docs/                 # ドキュメント
```

### スケーラビリティ設計
- **ドメイン駆動設計**: ビジネスロジックの分離
- **拡張可能認証**: Card・NFC・QR・生体認証対応
- **API バージョニング**: v1・v2対応
- **マルチテナント基盤**: 複数組織対応準備
- **非同期処理**: 高性能・高並行性

## 🛠️ 動作環境

- **Python**: 3.9以上
- **データベース**: SQLite・PostgreSQL
- **キャッシュ**: Redis
- **ハードウェア**: PaSoRi RC-S380（オプション、macOS推奨）
- **対応OS**: Windows 10/11, macOS, Linux
- **対応デバイス**: iPhone（Suica）・Android（NFC）

## ⚡ クイックスタート

### 1. リポジトリのクローン
```bash
git clone https://github.com/tsuyoshi-sk/attendance_system.git
cd attendance_system
```

### 2. Poetry環境セットアップ
```bash
# Poetryインストール（未インストールの場合）
curl -sSL https://install.python-poetry.org | python3 -

# 依存関係インストール
poetry install

# 仮想環境アクティベート
poetry shell
```

### 3. 環境設定
```bash
# 環境変数ファイル作成
cp .env.example .env

# 重要: 本番環境では以下を必ず変更
JWT_SECRET_KEY=your-64-character-secret-key-here-please-change-in-production
SECRET_KEY=your-64-character-app-secret-key-here-please-change-in-production
```

### 4. データベース初期化
```bash
# マイグレーション実行
alembic upgrade head

# 初期データ作成（オプション）
python scripts/seed_test_data.py
```

### 5. アプリケーション起動
```bash
# 開発モード
poetry run attendance-server

# または
uvicorn backend.app.main:app --reload

# 本番モード
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 6. PWA起動（オプション）
```bash
cd pwa
npm install
npm run dev
```

## 📱 使い方

### 基本操作

#### 1. 管理者アカウント作成
```bash
python scripts/create_admin.py
```

#### 2. 従業員登録
- ブラウザで http://localhost:8000/docs にアクセス
- `/api/v1/admin/employees` で従業員を作成
- `/api/v1/admin/employees/{id}/card` でカードを登録

#### 3. 打刻方法
- **PaSoRi**: カードをPaSoRiにかざす
- **iPhone**: Suicaアプリでタップ
- **Android**: NFCでタップ
- **PWA**: ブラウザから手動打刻

#### 4. レポート確認
- 日次レポート: `/api/v1/reports/daily/{date}`
- 月次レポート: `/api/v1/reports/monthly/{month}`

### 高度な機能

#### API バージョニング
- **v1**: 現在の安定版 `/api/v1/`
- **v2**: 将来の拡張版 `/api/v2/`（開発中）

#### 認証プロバイダー
```python
# 複数認証方式対応
providers = {
    "card": CardAuthProvider(),      # PaSoRi
    "nfc": NFCAuthProvider(),        # iPhone/Android
    "qr": QRAuthProvider(),          # QRコード
    "biometric": BiometricProvider() # 生体認証（将来）
}
```

## 🔧 開発

### 開発コマンド
```bash
# テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=backend --cov-report=html

# コード品質チェック
black .                    # フォーマット
isort .                    # インポート整理
flake8 .                   # リント
mypy backend/              # 型チェック

# セキュリティチェック
bandit -r backend/         # 脆弱性スキャン
safety check               # 依存関係チェック

# 品質チェック（全チェック実行）
make quality

# CI/CDパイプライン（ローカル実行）
make ci
```

### Docker実行
```bash
# 開発環境
docker-compose up -d

# 本番環境
docker-compose -f docker-compose.prod.yml up -d

# ヘルスチェック
curl http://localhost:8000/health
```

## 📊 運用・監視

### ヘルスチェック機能
- **基本ヘルスチェック**: `/health`
- **詳細ヘルスチェック**: `/health/detailed`
- **システムメトリクス**: `/metrics`
- **依存関係チェック**: `/health/dependencies`

### ログシステム
```bash
# ログ確認
tail -f logs/app.log          # アプリケーションログ
tail -f logs/security.log     # セキュリティ監査ログ
tail -f logs/performance.log  # パフォーマンスログ
tail -f logs/error.log        # エラーログ
```

### 監視ダッシュボード
- **システム監視**: CPU・メモリ・ディスク使用率
- **アプリケーション監視**: リクエスト数・レスポンス時間
- **セキュリティ監視**: 認証試行・不正アクセス
- **ビジネス監視**: 打刻数・従業員状況

## 🚀 デプロイメント

### GitHub Actions自動デプロイ
```yaml
# ステージング環境
git push origin feature/your-feature

# 本番環境
git push origin main
```

### 手動デプロイ
```bash
# Docker イメージビルド
docker build -t attendance-system:latest .

# 本番環境デプロイ
docker run -d \
  --name attendance-system \
  -p 8000:8000 \
  -e JWT_SECRET_KEY=your-secret \
  attendance-system:latest
```

## 🔮 ロードマップ

### v2.1 (2024 Q2)
- [ ] GraphQL API
- [ ] リアルタイム通知
- [ ] SSO・SAML認証

### v2.2 (2024 Q3)
- [ ] モバイルアプリ
- [ ] 顔認証機能
- [ ] 多言語対応

### v2.3 (2024 Q4)
- [ ] AI分析機能
- [ ] 予測機能
- [ ] BI連携

## 🤝 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

### 開発ガイドライン
- **Clean Architecture**: ドメイン層を意識した設計
- **テスト駆動**: 80%以上のカバレッジ維持
- **セキュリティ**: 脆弱性スキャン必須
- **コード品質**: Black・isort・flake8・mypy準拠

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照

## 🆘 サポート

- **バグ報告**: [Issues](https://github.com/tsuyoshi-sk/attendance_system/issues)
- **機能要望**: [Discussions](https://github.com/tsuyoshi-sk/attendance_system/discussions)
- **セキュリティ**: security@example.com

## 👨‍💻 作者

- **GitHub**: [@tsuyoshi-sk](https://github.com/tsuyoshi-sk)
- **Email**: contact@example.com

---

**🚀 Enterprise-Ready • 🔒 Security-First • 📱 Multi-Platform • ⚡ High-Performance**

*Built with ❤️ using FastAPI, Clean Architecture, and modern best practices*