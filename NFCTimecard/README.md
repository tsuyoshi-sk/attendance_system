# NFCTimecard - iPhone Suica対応勤怠管理アプリ

## 概要

NFCTimecardは、既存の勤怠管理システムと連携してiPhone内蔵のSuicaを使用した打刻を可能にするネイティブiOSアプリケーションです。PWAからカスタムURLスキームで起動され、NFC読み取り結果をWebSocket経由で返します。

## 技術スタック

- **言語**: Swift 5.0+
- **UI Framework**: SwiftUI
- **最小iOS**: iOS 14.0
- **必要な機能**: Core NFC
- **通信**: URLSession (HTTP/WebSocket)

## アーキテクチャ

```
PWA → カスタムURL → ネイティブアプリ → Core NFC → Suica IDm取得
                                    ↓
                            バックエンドAPI ← HTTP POST
                                    ↓
                              WebSocket → PWA
```

## 主要機能

### ✅ 実装済み機能

1. **カスタムURLスキーム対応**
   - `nfc-timecard://scan` でアプリ起動
   - パラメータ解析（scan_id, client_id, callback）

2. **NFC読み取り機能**
   - FeliCa System Code 0003 (Suica) 対応
   - IDm取得・フォーマット変換
   - 3秒タイムアウト設定

3. **バックエンド通信**
   - `/api/v1/nfc/scan-result` エンドポイント
   - 自動リトライ機能（最大3回）
   - エラーハンドリング

4. **UI/UX**
   - 日本語対応
   - 視覚的フィードバック
   - エラーメッセージ表示
   - ダークモード対応

5. **セキュリティ**
   - IDmのメモリ内処理のみ
   - HTTPSサポート（本番環境）
   - scan_id一回限り使用

## ディレクトリ構造

```
NFCTimecard/
├── App/
│   ├── NFCTimecardApp.swift    # アプリエントリーポイント
│   └── Info.plist              # 権限・設定
├── Views/
│   ├── ContentView.swift       # メインUI
│   └── NFCScanView.swift       # NFC読み取り画面
├── Managers/
│   ├── NFCManager.swift        # NFC制御
│   ├── APIClient.swift         # API通信
│   └── URLSchemeHandler.swift  # URLスキーム処理
├── Models/
│   ├── ScanResult.swift        # データモデル
│   └── NFCError.swift          # エラー定義
├── Utils/
│   ├── Constants.swift         # 定数
│   └── Extensions.swift        # 拡張機能
└── Tests/                      # テストコード
```

## セットアップ手順

### 1. Xcodeプロジェクト作成

1. Xcode起動
2. Create New Project → iOS → App
3. Product Name: NFCTimecard
4. Interface: SwiftUI
5. Language: Swift

### 2. プロジェクト設定

1. **Bundle Identifier**: `com.yourcompany.nfctimecard`
2. **Deployment Target**: iOS 14.0
3. **Device**: iPhone only

### 3. 必要な権限設定

Info.plistに以下を追加:

```xml
<key>NFCReaderUsageDescription</key>
<string>勤怠管理のためにSuicaを読み取ります</string>

<key>com.apple.developer.nfc.readersession.felica.systemcodes</key>
<array>
    <string>0003</string>
</array>
```

### 4. Capabilities追加

1. Signing & Capabilities タブ
2. "+ Capability" → Near Field Communication Tag Reading

### 5. ビルド・実行

1. 実機をMacに接続（NFC対応iPhone）
2. Scheme選択 → 実機選択
3. Build & Run (⌘R)

## 使用方法

### PWAからの起動

```javascript
// PWA側のコード例
const scanId = `scan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
const clientId = 'pwa_client_123';
const url = `nfc-timecard://scan?scan_id=${scanId}&client_id=${clientId}&callback=ws`;

window.location.href = url;
```

### 動作フロー

1. PWAが上記URLでアプリを起動
2. アプリがパラメータを解析
3. NFC読み取り画面を表示
4. ユーザーがSuicaをかざす
5. IDm取得・フォーマット
6. バックエンドAPIに送信
7. 成功時は自動的にPWAに戻る

## エラーハンドリング

### 対応エラー種別

- `nfcNotAvailable`: NFC機能が利用できません
- `nfcDisabled`: NFC機能を有効にしてください
- `multipleCardsDetected`: 複数のカードが検出されました
- `readTimeout`: 読み取りタイムアウト
- `unsupportedCard`: 対応していないカード
- `networkError`: ネットワークエラー
- `apiError`: APIエラー

## テスト

### ユニットテスト実行

```bash
swift test
```

### デバッグモード

ContentViewでデバッグモードを有効化すると、テスト用のボタンが表示されます。

## トラブルシューティング

### NFC読み取りができない

1. iPhone 7以降か確認
2. Settings → NFC が有効か確認
3. Suicaが登録されているか確認

### アプリが起動しない

1. URLスキームが正しく設定されているか確認
2. Info.plistの設定を確認

### API通信エラー

1. バックエンドが起動しているか確認
2. ネットワーク接続を確認
3. Info.plistのApp Transport Security設定確認

## 本番環境への移行

1. **API URLの変更**
   - `Constants.swift`の`API.BASE_URL`を本番URLに変更

2. **HTTPS対応**
   - Info.plistのNSAppTransportSecurityを削除または調整

3. **証明書ピニング**
   - 必要に応じてSSL証明書ピニングを実装

4. **ログ削除**
   - print文を削除またはDEBUGフラグで制御

## ライセンス

Copyright (c) 2024 Your Company. All rights reserved.

## 貢献者

- 4並行AI開発プロジェクトチーム
- Claude Code (実装担当)