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

## 🚀 今すぐ始める

**5分で動かしたい** → [クイックスタート](QUICKSTART.md)  
**詳しく知りたい** → このREADMEを読み進める

## ⚡ 概要

このシステムは4並行AI開発により1ヶ月で構築された、エンタープライズレベルの勤怠管理システムです。

### 主な特徴
- 📱 **iPhone Suica対応** - 世界初の実装
- 🔐 **OWASP ASVS Level 2** - エンタープライズセキュリティ
- 📊 **リアルタイム分析** - WebSocket + PWA
- 🏗️ **Clean Architecture** - 保守性重視の設計

## 🎯 主要機能

### 🔥 基本機能
- 🚪 **多様な打刻方式**: PaSoRi RC-S380・iPhone Suica・Android NFC・QRコード対応
- 👥 **無制限従業員管理**: エンタープライズ対応
- 🏢 **部署・チーム管理**: 階層的組織管理
- 🔐 **本格認証システム**: JWT・RBAC（ロールベースアクセス制御）
- 📊 **高度分析機能**: リアルタイム分析・予測機能
- 🌐 **マルチテナント基盤**: 複数組織対応準備済み

### ⚡ エンタープライズ機能
- 🏗️ **Clean Architecture**: ドメイン駆動設計
- 📈 **スケーラビリティ**: 数千名規模対応
- 🔒 **最高セキュリティ**: OWASP ASVS Level 2準拠
- 🚀 **自動CI/CD**: GitHub Actions完備
- 📱 **PWA対応**: オフライン動作可能
- 🔍 **包括的監視**: パフォーマンス・セキュリティ監視

## 🛠️ 動作環境

### 必須要件
- **Python**: 3.9以上（3.11推奨）
- **データベース**: SQLite（開発）・PostgreSQL（本番）
- **OS**: Windows 10/11, macOS 11+, Ubuntu 20.04+

### ハードウェア（オプション）
- **推奠**: Sony RC-S380（macOS/Windows/Linux対応）
- **旧型**: Sony RC-S300（Windowsのみ推奨）
- **環境変数**: `PASORI_DEVICE_ID`で指定可能

## 🚧 macOS セットアップ（RC-S380使用時）

### 1. libusb権限設定
```bash
# Homebrewでlibusb インストール
brew install libusb

# Python nfcpyインストール
pip install nfcpy==1.0.4
```

### 2. macOS 14.6+ SIP回避（必要な場合）
```bash
# 一時的にSIPを無効化（再起動が必要）
csrutil disable

# RC-S380接続テスト
python -m nfc

# SIPを再度有効化
csrutil enable
```

### 3. デバイス接続確認
```bash
# 環境変数でデバイス指定（オプション）
export PASORI_DEVICE_ID="usb:054c:06c1"  # RC-S380
# export PASORI_DEVICE_ID="usb:054c:0dc9"  # RC-S300

# 接続テスト
python hardware/pasori_test.py
```

## 🔒 セキュリティ

### 実装済みセキュリティ対策
- **JWT認証**: 64文字以上の強力なシークレットキー
- **データ暗号化**: カードIDmのSHA-256ハッシュ化
- **SQL インジェクション対策**: SQLAlchemy ORM使用
- **XSS/CSRF対策**: セキュリティヘッダー完備
- **監査ログ**: 全操作の追跡可能
- **レート制限**: ブルートフォース攻撃対策

### CI/CDセキュリティ
- **自動脆弱性スキャン**: Bandit・Safety
- **依存関係チェック**: Poetry/pip-audit
- **シークレット検出**: git-secrets統合
- **コード品質**: Black・Flake8・mypy

## 📊 システムアーキテクチャ

```
attendance_system/
├── backend/          # FastAPIバックエンド
│   ├── app/         # APIエンドポイント
│   ├── domain/      # ビジネスロジック
│   └── services/    # サービス層
├── pwa/             # Progressive Web App
├── hardware/        # ハードウェア制御
│   └── card_reader.py  # RC-S380/RC-S300対応
├── config/          # 設定管理
└── tests/           # テストスイート
```

## 🧪 開発者向け情報

### テスト実行
```bash
# 単体テスト
pytest tests/unit/

# 統合テスト
pytest tests/integration/

# カバレッジレポート
pytest --cov=backend --cov-report=html
```

### コード品質チェック
```bash
# フォーマット
black backend/ tests/

# リント
flake8 backend/ tests/

# 型チェック
mypy backend/
```

## 🤝 コントリビューション

1. Forkする
2. Feature branchを作成（`git checkout -b feature/amazing-feature`）
3. 変更をコミット（`git commit -m 'Add amazing feature'`）
4. ブランチにPush（`git push origin feature/amazing-feature`）
5. Pull Requestを作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)を参照してください。

## 🙏 謝辞

- [nfcpy](https://github.com/nfcpy/nfcpy) - NFC/FeliCa通信ライブラリ
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Webフレームワーク
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORMライブラリ

## 📞 サポート

- **Issues**: [GitHub Issues](https://github.com/tsuyoshi-sk/attendance_system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tsuyoshi-sk/attendance_system/discussions)
- **Wiki**: [プロジェクトWiki](https://github.com/tsuyoshi-sk/attendance_system/wiki)

---

**© 2024 Attendance System Project. Built with ❤️ by 4並行AI開発チーム**