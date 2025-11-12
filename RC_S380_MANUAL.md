# RC-S380 iPhone Suica勤怠管理システム 運用マニュアル

## 🎯 システム概要

世界初のiPhone Suica対応勤怠管理システムの実機版です。Sony RC-S380を使用して、iPhone Suicaの物理的なかざし動作による勤怠打刻を実現します。

### 主要機能
- ✅ iPhone Suica/モバイルSuica対応
- ✅ 4種類の打刻（出勤/退勤/外出/戻り）
- ✅ オフライン対応（100件/7日間保持）
- ✅ 異常パターン検出
- ✅ セキュリティ強化（SHA-256、偽造検出）
- ✅ 音声フィードバック

## 📋 システム要件

### ハードウェア
- **カードリーダー**: Sony RC-S380/S または RC-S380/P
- **PC**: Apple Silicon Mac (M1/M2/M3)
- **OS**: macOS Sonoma 14.0以上

### ソフトウェア
- Python 3.8.10以上（3.11まで対応）
- Homebrew
- libusb
- nfcpy 1.0.4

## 🚀 セットアップ手順

### 1. RC-S380の接続
```bash
# RC-S380をUSBポートに接続
# 電源LEDが点灯することを確認
```

### 2. セットアップスクリプトの実行
```bash
# 実行権限を付与
chmod +x setup_rc_s380.sh

# セットアップ実行
./setup_rc_s380.sh
```

### 3. 動作確認
```bash
# デバイスリストの確認
python3 -m nfc

# 出力例:
# This is the 1.0.4 version of nfcpy run in Python 3.8.10
# on macOS-14.0-arm64-arm-64bit
# I'm now searching your system for contactless devices
# ** found usb:054c:06c1 at usb:020:004
```

## 🏃 システムの起動

### 手動起動
```bash
python3 rc_s380_attendance.py
```

### 自動起動（LaunchAgent）
```bash
# 状態確認
launchctl list | grep rc_s380

# 手動開始
launchctl start com.attendance.rc_s380

# 手動停止
launchctl stop com.attendance.rc_s380
```

## 📱 使用方法

### 基本的な打刻操作

1. **システム起動確認**
   ```
   🚀 RC-S380 iPhone Suica勤怠管理システムを起動します...
   ✅ RC-S380接続成功: usb:054c:06c1
   📱 iPhone Suicaをリーダーにかざしてください...
   ```

2. **iPhone Suicaをかざす**
   - RC-S380の上に iPhone を置く
   - 「ピッ」という音で認識完了

3. **打刻結果の確認**
   ```
   📱 カード検出: IDm=JE80F5250217373F
   ✅ 坂井毅史さん (SUICA001) - 経営企画部 のINを記録しました
   🎵 おはようございます！出勤を記録しました
   ```

### 打刻パターン

| 現在の状態 | 次の打刻 | 用途 |
|-----------|---------|------|
| なし | IN | 出勤 |
| IN | OUT | 退勤 |
| IN | OUTSIDE | 外出 |
| OUTSIDE | RETURN | 戻り |
| RETURN | OUT | 退勤 |

## 🔒 セキュリティ機能

### カード認証
- SHA-256によるIDmハッシュ化
- Felica/Suicaシステムコード検証
- 偽造カード検出機能

### 重複防止
- 3分間の重複打刻防止
- 連続同一タイプ打刻の警告

### 異常検出
- 深夜早朝の異常時刻検出
- 打刻漏れ検出
- 12時間超の長時間労働警告

## 📊 データ管理

### データベース構造
```sql
-- 打刻記録
punch_records
├── employee_id      # 従業員ID
├── punch_type       # IN/OUT/OUTSIDE/RETURN
├── punch_time       # 打刻時刻
├── device_type      # iPhone_Suica_RC-S380
├── device_id        # 元のIDm（監査用）
└── is_offline       # オフライン打刻フラグ

-- 日次サマリー
daily_summaries
├── employee_id      # 従業員ID
├── date            # 日付
├── first_punch_in  # 最初の出勤時刻
├── last_punch_out  # 最後の退勤時刻
└── total_work_hours # 総労働時間
```

### オフライン対応
- ネットワーク障害時も打刻継続
- 最大100件、7日間保持
- 復旧時に自動同期

## 🛠 トラブルシューティング

### RC-S380が認識されない
```bash
# USB接続を確認
system_profiler SPUSBDataType | grep -A 5 "RC-S380"

# 権限確認（必要な場合）
sudo python3 rc_s380_attendance.py

# 他のプロセスがデバイスを使用していないか確認
lsof | grep -i nfc
```

### カードが読み取れない
1. iPhone の NFC が有効か確認
2. Suicaアプリが起動していないか確認
3. カードを正しい位置に置いているか確認
4. 3秒以上かざし続ける

### エラーメッセージ対応

| エラー | 原因 | 対処法 |
|--------|------|---------|
| ❌ RC-S380の接続に失敗 | デバイス未接続 | USB接続確認 |
| ⚠️ 未登録のカード | IDm未登録 | 管理者に登録依頼 |
| ⚠️ 既に打刻済み | 3分以内の重複 | 3分後に再試行 |
| ⚠️ 不正なカード | 偽造/非対応カード | 正規のSuica使用 |

## 📈 統計・レポート

### ログファイル
```bash
# アプリケーションログ
tail -f logs/rc_s380_attendance.log

# システムログ（LaunchAgent使用時）
tail -f logs/rc_s380_stdout.log
tail -f logs/rc_s380_stderr.log
```

### 打刻履歴の確認
```sql
-- 本日の打刻一覧
SELECT e.name, p.punch_type, p.punch_time
FROM punch_records p
JOIN employees e ON p.employee_id = e.id
WHERE DATE(p.punch_time) = DATE('now')
ORDER BY p.punch_time DESC;

-- 月次勤怠サマリー
SELECT e.name, COUNT(*) as days, SUM(d.total_work_hours) as total_hours
FROM daily_summaries d
JOIN employees e ON d.employee_id = e.id
WHERE strftime('%Y-%m', d.date) = strftime('%Y-%m', 'now')
GROUP BY e.id;
```

## 🔧 メンテナンス

### 日次メンテナンス
```bash
# オフライン打刻の同期確認
sqlite3 offline_punch_queue.db "SELECT COUNT(*) FROM offline_punches;"

# ログローテーション（7日以上のログを圧縮）
find logs -name "*.log" -mtime +7 -exec gzip {} \;
```

### 月次メンテナンス
```bash
# データベースの最適化
sqlite3 attendance.db "VACUUM;"

# バックアップ
cp attendance.db "data/backups/attendance_$(date +%Y%m%d).db"
```

## 📞 サポート

### よくある質問

**Q: 複数のiPhone Suicaを登録できますか？**
A: はい、管理画面から従業員ごとに登録可能です。

**Q: Apple Watchでも使えますか？**
A: Suica対応のApple Watchであれば使用可能です。

**Q: オフライン時のデータは失われませんか？**
A: 最大100件、7日間保持されます。

### 問い合わせ先
- システム管理者: 経営企画部
- 技術サポート: GitHub Issues

## 🎉 付録

### 登録済みテストデータ
| 従業員名 | 従業員コード | iPhone Suica IDm | 部署 |
|---------|-------------|------------------|------|
| 坂井毅史 | SUICA001 | JE80F5250217373F | 経営企画 |

### コマンドリファレンス
```bash
# システム起動
python3 rc_s380_attendance.py

# デバイステスト
python3 -m nfc

# データベース確認
sqlite3 attendance.db ".tables"

# ログ確認
tail -f logs/rc_s380_attendance.log
```

---
**Version**: 1.0.0  
**Last Updated**: 2024-02-XX  
**System**: RC-S380 iPhone Suica Attendance System