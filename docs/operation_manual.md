# 勤怠管理システム運用手順書

## 目次

1. [システム起動・停止](#システム起動停止)
2. [日常運用](#日常運用)
3. [トラブルシューティング](#トラブルシューティング)
4. [メンテナンス作業](#メンテナンス作業)
5. [バックアップとリストア](#バックアップとリストア)
6. [監視とアラート](#監視とアラート)

## システム起動・停止

### システム起動手順

1. **環境準備**
```bash
cd /path/to/attendance_system
source .venv/bin/activate
```

2. **設定確認**
```bash
# 環境変数の確認
make check-env

# データベース接続確認
make db-check
```

3. **サービス起動**
```bash
# 開発環境
make dev

# 本番環境
make production
```

4. **起動確認**
```bash
# ヘルスチェック
curl http://localhost:8000/health

# ログ確認
tail -f logs/app.log
```

### システム停止手順

1. **グレースフルシャットダウン**
```bash
# Ctrl+C または
kill -SIGTERM <process_id>
```

2. **強制停止（緊急時のみ）**
```bash
kill -SIGKILL <process_id>
```

3. **停止確認**
```bash
ps aux | grep uvicorn
```

## 日常運用

### 打刻状況確認

1. **リアルタイム監視**
```bash
# 打刻ログの監視
tail -f logs/punch.log | grep -E "打刻成功|打刻失敗"

# 現在の打刻状況確認
curl http://localhost:8000/api/v1/punch/status/{employee_id}
```

2. **日次集計確認**
```bash
# 特定日の打刻履歴
curl "http://localhost:8000/api/v1/punch/history/{employee_id}?date=2023-12-01"
```

### オフラインキュー管理

1. **キュー状態確認**
```bash
curl http://localhost:8000/api/v1/punch/offline/status
```

2. **手動同期（必要時）**
```bash
python scripts/sync_offline_queue.py
```

### PaSoRi管理

1. **接続状態確認**
```bash
# PaSoRiテストツール実行
python hardware/pasori_test.py

# 接続診断
python hardware/pasori_test.py --check
```

2. **トラブル時の対処**
```bash
# USB再接続
# 1. PaSoRiを物理的に抜く
# 2. 5秒待つ
# 3. 再接続
# 4. サービス再起動
```

## トラブルシューティング

### よくある問題と対処法

#### 1. PaSoRi接続エラー

**症状**: "PaSoRi接続エラー"が発生

**対処法**:
```bash
# USBデバイス確認
lsusb | grep Sony

# 権限確認
ls -la /dev/bus/usb/*/*

# udevルール再読み込み（Linux）
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 2. 重複打刻エラー

**症状**: 正常な打刻なのに重複エラー

**対処法**:
```bash
# 時刻同期確認
timedatectl status

# NTP同期
sudo systemctl restart ntp
```

#### 3. データベースエラー

**症状**: "Database connection error"

**対処法**:
```bash
# データベース状態確認
make db-check

# データベース再起動（PostgreSQLの場合）
sudo systemctl restart postgresql

# 接続数確認
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

#### 4. オフラインキュー満杯

**症状**: "OFFLINE_QUEUE_FULL"エラー

**対処法**:
```bash
# キューサイズ確認
sqlite3 data/offline_queue.db "SELECT COUNT(*) FROM offline_punches;"

# 古いレコード削除
python scripts/cleanup_offline_queue.py --days 7
```

### ログ調査手順

1. **エラーログ確認**
```bash
# 最新のエラー
tail -n 100 logs/error.log | grep ERROR

# 特定時刻のエラー
grep "2023-12-01 09:" logs/error.log
```

2. **パフォーマンスログ確認**
```bash
# 遅いリクエスト
cat logs/performance.log | jq 'select(.duration_ms > 1000)'
```

3. **セキュリティログ確認**
```bash
# 不正アクセス試行
grep "SECURITY" logs/security_audit.log
```

## メンテナンス作業

### 定期メンテナンス

#### 月次作業

1. **ログローテーション確認**
```bash
# ログサイズ確認
du -sh logs/*

# 手動ローテーション（必要時）
logrotate -f /etc/logrotate.d/attendance
```

2. **データベース最適化**
```bash
# PostgreSQL
psql -c "VACUUM ANALYZE;"

# SQLite
sqlite3 data/attendance.db "VACUUM;"
```

3. **古いデータのアーカイブ**
```bash
python scripts/archive_old_data.py --months 12
```

#### 年次作業

1. **セキュリティ監査**
```bash
# パスワードポリシー確認
python scripts/security_audit.py

# 証明書更新確認
openssl x509 -in cert.pem -noout -dates
```

### アップデート手順

1. **事前準備**
```bash
# バックアップ作成
make backup

# 依存関係確認
pip list --outdated
```

2. **アップデート実施**
```bash
# コード更新
git pull origin main

# 依存関係更新
pip install -r requirements.txt --upgrade

# データベースマイグレーション
alembic upgrade head
```

3. **動作確認**
```bash
# テスト実行
pytest

# ヘルスチェック
curl http://localhost:8000/health
```

## バックアップとリストア

### 自動バックアップ

設定済みの場合、毎日午前2時に自動実行されます。

### 手動バックアップ

```bash
# フルバックアップ
make backup

# データベースのみ
make db-backup

# 設定ファイルのみ
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/
```

### リストア手順

1. **サービス停止**
```bash
make stop
```

2. **リストア実行**
```bash
# データベース
make db-restore BACKUP_FILE=backup_20231201.sql

# 設定ファイル
tar -xzf config_backup_20231201.tar.gz -C config/
```

3. **動作確認**
```bash
make start
make test
```

## 監視とアラート

### ヘルスチェック

1. **自動監視設定**
```bash
# crontab設定例
*/5 * * * * /path/to/check_health.sh
```

2. **手動チェック**
```bash
# 総合ヘルスチェック
curl http://localhost:8000/health | jq

# 個別チェック
python scripts/health_check.py --verbose
```

### アラート設定

1. **Slack通知**
```bash
# .envで設定
SLACK_ENABLED=True
SLACK_TOKEN="xoxb-your-token"
SLACK_CHANNEL="#alerts"
```

2. **メール通知**
```bash
# .envで設定
MAIL_ENABLED=True
MAIL_SERVER="smtp.example.com"
```

### パフォーマンスモニタリング

1. **メトリクス確認**
```bash
# Prometheusメトリクス
curl http://localhost:9090/metrics
```

2. **レスポンスタイム監視**
```bash
# 平均レスポンスタイム
cat logs/performance.log | jq '.duration_ms' | awk '{sum+=$1} END {print sum/NR}'
```

## 緊急時対応

### システム障害時

1. **初期対応**
```bash
# 状態確認
systemctl status attendance
journalctl -u attendance -n 100

# 緊急再起動
systemctl restart attendance
```

2. **原因調査**
```bash
# エラーログ収集
./scripts/collect_logs.sh

# デバッグモード起動
DEBUG=True python -m uvicorn backend.app.main:app --reload
```

### データ復旧

1. **打刻データ復旧**
```bash
# オフラインキューから復旧
python scripts/recover_from_offline.py

# バックアップから復旧
python scripts/restore_punch_data.py --date 2023-12-01
```

## セキュリティ対応

### 不正アクセス検知時

1. **即時対応**
```bash
# IPブロック
iptables -A INPUT -s <suspicious_ip> -j DROP

# ログ確認
grep <suspicious_ip> logs/security_audit.log
```

2. **事後対応**
```bash
# セキュリティ監査実行
python scripts/security_scan.py

# パスワードリセット要求
python scripts/force_password_reset.py --all-users
```

## 連絡先

### 緊急連絡先

- システム管理者: admin@example.com
- 開発チーム: dev-team@example.com
- サポート: support@example.com

### エスカレーション

1. レベル1: 運用チーム対応（15分以内）
2. レベル2: 開発チーム対応（30分以内）
3. レベル3: 管理者対応（1時間以内）