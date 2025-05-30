# 🎯 FeliCa勤怠システム - iPhone Suica対応

## 概要
物理カード・iPhone Suica・Android Suica全対応の勤怠管理システム

## 🚀 セットアップ

### 1. 必要なハードウェア
- **Sony PaSoRi RC-S380** (USB FeliCaリーダー)
- 対応カード:
  - 物理Suica/PASMO
  - iPhone Suica (Express Transit Card)
  - Android Suica/モバイルPASMO

### 2. ソフトウェアセットアップ
```bash
# 依存関係インストール
pip install -r requirements_felica.txt

# セットアップスクリプト実行
./setup_felica.sh

# データベースマイグレーション
python migrate_felica.py
```

### 3. USB権限設定（Linux）
```bash
# udevルール作成（自動実行済み）
sudo tee /etc/udev/rules.d/99-felica.rules << EOF
# RC-S380 (Recommended)
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="06c3", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="0689", MODE="0666"
# RC-S300 (Legacy)
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="01bb", MODE="0666"
EOF

sudo udevadm control --reload-rules
```

## 📱 使い方

### RC-S380の場合（推奨）
```bash
# デバイス接続確認
python felica_reader.py --check

# 通常起動（連続読み取り）
python felica_reader.py

# カード登録モード
python felica_reader.py --register 1

# 別のサーバーを指定
python felica_reader.py --url http://192.168.1.100:8001
```

### RC-S300の場合（レガシー）
```bash
# 通常起動（連続読み取り）
python felica_reader_rcs300.py

# カード登録モード
python felica_reader_rcs300.py --register 1
```

## 🔌 API エンドポイント

### FeliCa勤怠記録
```
POST /api/felica-attendance
{
  "felica_idm": "012345678ABCDEF0",
  "timestamp": "2025-05-29T12:00:00",
  "reader_id": "reader-001",
  "method": "felica"
}
```

### FeliCaカード登録
```
POST /api/admin/felica/register
{
  "user_id": 1,
  "felica_idm": "012345678ABCDEF0"
}
```

## 🧪 動作テスト

### APIテスト（ハードウェア不要）
```bash
python test_felica_api.py
```

### RC-S380実機テスト手順
1. RC-S380をUSB接続
2. デバイス確認: `python felica_reader.py --check`
3. 読み取り開始: `python felica_reader.py`
4. カードをリーダーにタッチ
5. 画面に結果表示

### RC-S300実機テスト手順（レガシー）
1. RC-S300をUSB接続
2. デバイス確認: `python felica_reader_rcs300.py --check`
3. 読み取り開始: `python felica_reader_rcs300.py`
4. カードをリーダーにタッチ
5. 画面に結果表示

## 💡 トラブルシューティング

### "pafe未インストール"エラー（RC-S380用）
```bash
pip install pafe pyusb
```

### "nfcpy未インストール"エラー（RC-S380用）
```bash
pip install nfcpy
```

### USBデバイスが見つからない
```bash
# デバイス確認
lsusb | grep Sony

# 権限確認（Linux）
ls -la /dev/bus/usb/*/*
```

### カード読み取りできない
- リーダーのLEDが点灯しているか確認
- カードを1秒以上タッチ
- iPhone: Wallet設定でExpress Transit Card有効化

## 📊 データベース構造

### felica_registrations テーブル
- `id`: 主キー
- `user_id`: ユーザーID（外部キー）
- `felica_idm`: FeliCa IDM（16文字）
- `registered_at`: 登録日時
- `is_active`: 有効フラグ

### attendance_records テーブル（拡張）
- `felica_idm`: FeliCa IDM（NULL可）

## 🔒 セキュリティ
- IDMは平文で保存（Suicaと同じ仕様）
- 重複読み取り防止（2秒間）
- カード登録は管理者権限必要

## 📱 iPhone Suica設定
1. Walletアプリでカード選択
2. カード詳細 → Express Transit Card
3. 「エクスプレスカード」をON
4. Face ID/Touch ID不要で読み取り可能に

## 🎯 今後の拡張
- [ ] 複数リーダー対応
- [ ] カード種別判定（Suica/PASMO）
- [ ] 残高読み取り（要追加権限）
- [ ] 定期券区間表示