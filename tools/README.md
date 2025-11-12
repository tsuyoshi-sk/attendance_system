# Tools ディレクトリ

勤怠管理システムの補助ツール集

## 📱 pasori_reader.py

PaSoRiカードリーダーを使った連続打刻スクリプト

### 機能

- カードをタップするたびに、**自動的に打刻タイプを切り替え**
- 打刻順序: `in → outside → return → out` （ループ）
- APIに自動ログイン＆JWT認証
- リアルタイムで結果を表示

### 必要なもの

#### ハードウェア
- Sony PaSoRi RC-S380（推奨）または RC-S300
- FeliCaカード（Suica、PASMO、社員証など）

#### ソフトウェア
```bash
# nfcpyとrequestsをインストール
pip install nfcpy requests

# macOSの場合は追加でlibusb
brew install libusb
```

### 使い方

#### 基本的な使い方

```bash
# デフォルト設定で起動（localhost:8080, admin/admin123!）
python tools/pasori_reader.py
```

#### 環境変数でカスタマイズ

```bash
# カスタムAPI URLとユーザー
API_BASE=http://192.168.1.100:8080 \
API_USER=admin \
API_PASS=your_password \
python tools/pasori_reader.py
```

#### .envファイルで設定

```bash
# .env.reader ファイルを作成
cat > .env.reader << 'EOF'
API_BASE=http://localhost:8080
API_USER=admin
API_PASS=admin123!
EOF

# .envファイルを読み込んで起動
set -a; source .env.reader; set +a
python tools/pasori_reader.py
```

### 実行例

```
============================================================
PaSoRi カードリーダー連続打刻スクリプト
============================================================
API Base URL: http://localhost:8080
User: admin
打刻順序: in → outside → return → out
============================================================
[i] ログイン中... (user=admin)
[i] ログイン成功
[i] デバイス接続試行: usb
[✓] デバイス接続成功: usb
[i] リーダー情報: <nfc.clf.device.Device object at 0x...>

============================================================
[i] カードをタップしてください（Ctrl+Cで終了）
============================================================

[+] タップ検知: IDm=0123456789abcdef
    → 打刻タイプ: in
    ✓ 成功 [200]: 出勤を記録しました

[+] タップ検知: IDm=0123456789abcdef
    → 打刻タイプ: outside
    ✓ 成功 [200]: 外出を記録しました

[+] タップ検知: IDm=0123456789abcdef
    → 打刻タイプ: return
    ✓ 成功 [200]: 戻りを記録しました

[+] タップ検知: IDm=0123456789abcdef
    → 打刻タイプ: out
    ✓ 成功 [200]: 退勤を記録しました
```

### トラブルシューティング

#### リーダーが見つからない

```
[✗] PaSoRiリーダーをオープンできませんでした
```

**対処方法:**

1. **USB接続を確認**
   ```bash
   # macOS: システム情報でUSBデバイスを確認
   system_profiler SPUSBDataType | grep -A 10 Sony
   ```

2. **libusbをインストール（macOS）**
   ```bash
   brew install libusb
   ```

3. **nfcpyを再インストール**
   ```bash
   pip uninstall nfcpy
   pip install nfcpy==1.0.4
   ```

4. **権限エラーの場合はsudoで実行**
   ```bash
   sudo python tools/pasori_reader.py
   ```

5. **デバイスIDを明示的に指定**
   ```python
   # pasori_reader.py の candidates を編集
   candidates = [
       "usb:054c:06c1",    # RC-S380
       "usb:054c:0dc9",    # RC-S300
   ]
   ```

#### 重複エラーが頻発する

```
⚠ 重複エラー [409]: 3分以上待ってから再試行してください
```

**原因:** 同じ打刻タイプを3分以内に連続で送信している

**対処方法:**
- カードを離してから3分待つ
- または、次の打刻タイプ（外出→戻り）にスキップする

#### 認証エラー

```
[!] ログインエラー: 401 Unauthorized
```

**対処方法:**
1. ユーザー名とパスワードを確認
2. APIサーバーが起動しているか確認
   ```bash
   curl http://localhost:8080/health
   ```

### 開発者向け情報

#### デバッグモード

```python
# pasori_reader.py にデバッグ出力を追加
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### カスタム打刻順序

```python
# PUNCH_ORDER を変更
PUNCH_ORDER = ["in", "out"]  # シンプルな出勤/退勤のみ
```

#### タイムアウト調整

```python
# デバウンス時間を変更（秒）
time.sleep(1.5)  # → time.sleep(3.0) などに変更
```

## その他のツール

今後、以下のようなツールを追加予定：

- `qr_generator.py` - QRコード打刻用のコード生成
- `bulk_import.py` - 従業員データの一括インポート
- `report_export.py` - レポートの一括エクスポート

---

**問題が解決しない場合は Issues で質問してください:**
https://github.com/tsuyoshi-sk/attendance_system/issues
