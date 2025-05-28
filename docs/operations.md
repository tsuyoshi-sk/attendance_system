# 勤怠管理システム運用マニュアル

## 目次
1. [システム概要](#システム概要)
2. [システム要件](#システム要件)
3. [初期セットアップ](#初期セットアップ)
4. [日常運用](#日常運用)
5. [トラブルシューティング](#トラブルシューティング)
6. [バックアップとリカバリ](#バックアップとリカバリ)
7. [セキュリティ管理](#セキュリティ管理)
8. [パフォーマンス監視](#パフォーマンス監視)

## システム概要

### アーキテクチャ構成
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   PWA App   │────▶│  Backend    │────▶│  Database   │
│ (Frontend)  │     │   (API)     │     │(PostgreSQL) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  iOS App    │     │   Redis     │     │   Backup    │
│    (NFC)    │     │  (Cache)    │     │  Storage    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 主要コンポーネント
- **Backend API**: FastAPI (Python 3.9+)
- **Database**: PostgreSQL 13+ / SQLite (開発環境)
- **Cache**: Redis 6+
- **Frontend**: PWA (Progressive Web App)
- **Mobile**: iOS App (NFC読み取り専用)

## システム要件

### ハードウェア要件
- **CPU**: 2コア以上
- **メモリ**: 4GB以上（推奨8GB）
- **ストレージ**: 20GB以上の空き容量
- **NFC リーダー**: PaSoRi RC-S380 (オプション)

### ソフトウェア要件
- **OS**: Ubuntu 20.04 LTS / macOS 11+ / Windows 10+
- **Python**: 3.9以上
- **Node.js**: 16以上（PWA開発用）
- **Docker**: 20.10以上（推奨）
- **PostgreSQL**: 13以上
- **Redis**: 6以上

## 初期セットアップ

### 1. 環境変数の設定
```bash
# .envファイルをコピー
cp .env.example .env

# .envファイルを編集
vim .env
```

**必須設定項目:**
```env
# セキュリティ
JWT_SECRET_KEY=<強力なランダム文字列>
SECRET_KEY=<強力なランダム文字列>

# データベース（本番環境）
DATABASE_URL=postgresql://user:password@localhost:5432/attendance_db

# Redis
REDIS_URL=redis://localhost:6379

# 環境
ENVIRONMENT=production
```

### 2. データベースセットアップ
```bash
# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt

# データベース初期化
python scripts/init_database.py

# マイグレーション実行
alembic upgrade head
```

### 3. 初期データ投入
```bash
# 管理者ユーザー作成
python scripts/create_admin.py

# テストデータ投入（開発環境のみ）
python scripts/seed_test_data.py
```

### 4. サービス起動
```bash
# 開発環境
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 本番環境（Docker使用）
docker-compose up -d
```

## 日常運用

### 打刻操作フロー
1. **出勤時**: NFCカードをリーダーにタッチ → 「出勤」自動判定
2. **外出時**: NFCタッチ → 「外出」を選択
3. **戻り時**: NFCタッチ → 「戻り」を選択
4. **退勤時**: NFCタッチ → 「退勤」自動判定

### 管理者タスク

#### 従業員登録
```bash
# APIエンドポイント
POST /api/v1/admin/employees
{
  "employee_code": "EMP001",
  "name": "山田太郎",
  "department": "開発部",
  "email": "yamada@example.com"
}
```

#### カード登録
1. 管理画面にログイン
2. 従業員を選択
3. 「カード登録」をクリック
4. NFCカードをリーダーにタッチ
5. 登録完了

#### レポート生成
```bash
# 日次レポート
GET /api/v1/reports/daily?date=2024-01-15

# 月次レポート
GET /api/v1/reports/monthly?year=2024&month=1

# CSVエクスポート
GET /api/v1/reports/export?format=csv&year=2024&month=1
```

### 定期メンテナンス

#### 日次タスク（毎日深夜2時）
```bash
# crontabに登録
0 2 * * * /path/to/venv/bin/python /path/to/scripts/daily_batch.py
```

**日次バッチ処理内容:**
- 前日の打刻データ集計
- 異常打刻の検出・通知
- 日次サマリー作成

#### 月次タスク（毎月1日深夜3時）
```bash
# crontabに登録
0 3 1 * * /path/to/venv/bin/python /path/to/scripts/monthly_batch.py
```

**月次バッチ処理内容:**
- 前月の勤怠集計
- 月次レポート生成
- データアーカイブ

## トラブルシューティング

### よくある問題と対処法

#### 1. NFCカードが読み取れない
```bash
# PaSoRiデバイスの確認
lsusb | grep Sony

# 権限設定確認
ls -la /dev/bus/usb/*/*

# udevルール再読み込み
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 2. データベース接続エラー
```bash
# PostgreSQL状態確認
sudo systemctl status postgresql

# 接続テスト
psql -h localhost -U attendance_user -d attendance_db

# 接続プール再設定
curl -X POST http://localhost:8000/api/v1/admin/reset-db-pool
```

#### 3. Redis接続エラー
```bash
# Redis状態確認
redis-cli ping

# メモリ使用状況
redis-cli info memory

# キャッシュクリア
redis-cli FLUSHDB
```

#### 4. APIレスポンスが遅い
```bash
# パフォーマンスログ確認
tail -f logs/performance.log

# 接続数確認
netstat -an | grep :8000 | wc -l

# ワーカー数調整
uvicorn backend.app.main:app --workers 4
```

### エラーコード一覧

| コード | 説明 | 対処法 |
|--------|------|--------|
| E001 | カード未登録 | カードを管理画面から登録 |
| E002 | 無効な打刻順序 | 前回の打刻状態を確認 |
| E003 | データベースエラー | DB接続を確認 |
| E004 | 認証エラー | トークンを再取得 |
| E005 | 権限不足 | ユーザーロールを確認 |

## バックアップとリカバリ

### バックアップ戦略

#### 自動バックアップ
```bash
# 日次バックアップスクリプト
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/attendance"

# データベースバックアップ
pg_dump attendance_db > $BACKUP_DIR/db_$DATE.sql

# ファイルバックアップ
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /app/data /app/logs

# 古いバックアップ削除（30日以上）
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

#### 手動バックアップ
```bash
# フルバックアップ
python scripts/backup.py --type full --output /backup/manual/

# 差分バックアップ
python scripts/backup.py --type incremental --since 2024-01-01
```

### リストア手順

#### データベースリストア
```bash
# バックアップからリストア
psql attendance_db < /backup/db_20240115.sql

# 特定時点へのリストア
pg_restore -d attendance_db -t punch_records backup.dump
```

#### アプリケーションリストア
```bash
# ファイルリストア
tar -xzf /backup/files_20240115.tar.gz -C /

# 設定ファイル確認
diff .env .env.backup
```

## セキュリティ管理

### アクセス制御

#### ロール定義
- **admin**: 全機能アクセス可能
- **manager**: レポート閲覧、従業員管理
- **user**: 自分の打刻のみ

#### API認証フロー
```
1. POST /api/v1/auth/login
   → JWT トークン取得
2. リクエストヘッダーに追加
   Authorization: Bearer <token>
3. トークン有効期限: 24時間
```

### セキュリティチェックリスト

#### 日次チェック
- [ ] 不正アクセスログ確認
- [ ] 異常な打刻パターン検出
- [ ] システムリソース使用率

#### 週次チェック
- [ ] セキュリティパッチ適用
- [ ] SSL証明書有効期限
- [ ] バックアップ整合性

#### 月次チェック
- [ ] アクセス権限棚卸し
- [ ] パスワードポリシー確認
- [ ] 監査ログレビュー

### インシデント対応

#### 不正アクセス検知時
1. 該当IPアドレスをブロック
2. 影響範囲の調査
3. パスワード強制リセット
4. インシデントレポート作成

#### データ漏洩対応
1. システム緊急停止
2. 漏洩範囲の特定
3. 関係者への通知
4. 再発防止策の実施

## パフォーマンス監視

### 監視項目

#### システムメトリクス
```bash
# CPU使用率
top -bn1 | grep "Cpu(s)"

# メモリ使用率
free -m

# ディスク使用率
df -h

# ネットワーク接続数
netstat -an | grep ESTABLISHED | wc -l
```

#### アプリケーションメトリクス
- API応答時間
- データベースクエリ時間
- キャッシュヒット率
- エラー発生率

### パフォーマンスチューニング

#### データベース最適化
```sql
-- インデックス作成
CREATE INDEX idx_punch_employee_time ON punch_records(employee_id, punch_time);

-- 統計情報更新
ANALYZE punch_records;

-- バキューム実行
VACUUM ANALYZE;
```

#### アプリケーション最適化
```python
# 接続プールサイズ調整
MAX_CONNECTIONS_COUNT = 100
MIN_CONNECTIONS_COUNT = 10

# キャッシュTTL調整
CACHE_DEFAULT_TTL = 300  # 5分

# バッチサイズ調整
BATCH_MAX_SIZE = 100
```

### アラート設定

#### 閾値設定
- CPU使用率 > 80%
- メモリ使用率 > 90%
- API応答時間 > 1秒
- エラー率 > 1%

#### 通知先設定
```yaml
alerts:
  - type: email
    recipients:
      - admin@example.com
  - type: slack
    webhook: https://hooks.slack.com/xxx
```

## 付録

### コマンドリファレンス

#### 管理コマンド
```bash
# ユーザー管理
python manage.py create-user --role admin
python manage.py reset-password --email user@example.com

# データ管理
python manage.py export-data --format csv --output data.csv
python manage.py import-data --file data.csv

# システム管理
python manage.py check-health
python manage.py clear-cache
```

### 設定ファイルテンプレート

#### nginx.conf
```nginx
server {
    listen 80;
    server_name attendance.example.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### systemd サービス
```ini
[Unit]
Description=Attendance System API
After=network.target

[Service]
Type=simple
User=attendance
WorkingDirectory=/opt/attendance
Environment="PATH=/opt/attendance/venv/bin"
ExecStart=/opt/attendance/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### サポート情報

#### 技術サポート
- メール: support@attendance-system.com
- 営業時間: 平日 9:00-18:00
- 緊急連絡先: 080-xxxx-xxxx

#### ドキュメント
- API仕様書: `/docs`
- 開発者ガイド: `docs/developer_guide.md`
- FAQ: `docs/faq.md`