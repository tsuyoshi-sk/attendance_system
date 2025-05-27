# NFC勤怠管理システム

## 🎯 プロジェクト概要
iPhone（iOS）のNFC機能を使用した企業向け勤怠管理システム。Suicaカードをスキャンして出退勤を記録します。

## 🏗️ システム構成

### 4並行AI開発体制
- **Terminal A**: iOS NFC アプリ開発
- **Terminal B**: PWA WebSocket Client開発
- **Terminal C**: バックエンド最適化
- **Terminal D**: テスト・品質管理

## 🚀 主要機能

### iOS アプリ
- NFCカード（Suica）読み取り
- URL Scheme連携
- リアルタイムWebSocket通信

### PWA（Web アプリ）
- QRコード表示・読み取り
- WebSocket双方向通信
- オフライン対応
- プッシュ通知

### バックエンド
- FastAPI + WebSocket
- PostgreSQL データベース
- 非同期処理
- セキュリティ対策

## 📁 ディレクトリ構成

```
/
├── NFCTimecard/           # iOS アプリ（Swift）
├── attendance_system/     # バックエンド（Python/FastAPI）
├── pwa/                  # PWA フロントエンド
├── tests/                # テストスイート
├── quality/              # 品質管理・監視
├── .github/workflows/    # CI/CD設定
└── docs/                 # ドキュメント
```

## 🛠️ 技術スタック

### フロントエンド
- iOS: Swift 5, Core NFC
- PWA: HTML5, JavaScript, Service Worker
- WebSocket Client

### バックエンド
- Python 3.8+
- FastAPI
- SQLAlchemy
- PostgreSQL
- WebSocket

### インフラ・ツール
- Docker & Docker Compose
- GitHub Actions
- pytest, Selenium
- Locust（負荷テスト）

## 🚀 クイックスタート

### 必要条件
- macOS（iOS開発用）
- Xcode 14+
- Python 3.8+
- Node.js 18+
- Docker Desktop

### セットアップ

1. リポジトリのクローン
```bash
git clone https://github.com/yourusername/nfc-timecard-system.git
cd nfc-timecard-system
```

2. 依存関係のインストール
```bash
make install
```

3. 開発環境の起動
```bash
make dev
```

4. iOS アプリのビルド
```bash
cd NFCTimecard
open NFCTimecard.xcodeproj
# Xcodeでビルド・実行
```

## 🧪 テスト実行

```bash
# 全テスト実行
make test

# 個別テスト
make test-unit         # ユニットテスト
make test-integration  # 統合テスト
make test-performance  # パフォーマンステスト
make test-security     # セキュリティテスト
```

## 📊 品質管理

```bash
# 品質監視開始
python quality/monitoring/quality_monitor.py

# レポート生成
make report
```

## 🔒 セキュリティ

- JWT認証
- HTTPS通信
- SQLインジェクション対策
- XSS対策
- レート制限

## 📈 パフォーマンス

- WebSocket接続: 最大200並行接続対応
- API応答時間: P95 < 500ms
- スループット: 500+ req/sec

## 🤝 コントリビューション

1. Forkする
2. Feature branchを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. Branchにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 👥 開発チーム

4並行AI開発により実装:
- Terminal A: iOS開発担当
- Terminal B: PWA開発担当
- Terminal C: バックエンド担当
- Terminal D: 品質管理担当

## 📞 サポート

問題や質問がある場合は、Issueを作成してください。