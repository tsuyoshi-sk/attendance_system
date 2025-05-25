# エラーコード一覧

## 概要

勤怠管理システムで使用されるエラーコードとその対処方法を記載します。

## HTTPステータスコード別エラー

### 400 Bad Request

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| VALIDATION_ERROR | 入力値検証エラー | リクエストパラメータを確認してください |
| INVALID_SEQUENCE | 不正な打刻順序 | 現在の打刻状態を確認してください |
| INVALID_DATE_FORMAT | 日付形式エラー | YYYY-MM-DD形式で指定してください |

### 401 Unauthorized

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| UNAUTHORIZED | 認証エラー | 有効な認証トークンを使用してください |
| TOKEN_EXPIRED | トークン期限切れ | 再度ログインしてください |

### 403 Forbidden

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| PERMISSION_DENIED | 権限不足 | 必要な権限を持つアカウントでアクセスしてください |
| IP_BLOCKED | IPアドレスブロック | システム管理者に連絡してください |

### 404 Not Found

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| EMPLOYEE_NOT_FOUND | 従業員が見つかりません | カード登録状況を確認してください |
| RESOURCE_NOT_FOUND | リソースが見つかりません | URLを確認してください |
| CARD_NOT_FOUND | カードが見つかりません | カード登録を行ってください |

### 409 Conflict

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| DUPLICATE_PUNCH | 重複打刻エラー | 3分以上待ってから再試行してください |
| DUPLICATE_EMPLOYEE_CODE | 従業員コード重複 | 別の従業員コードを使用してください |
| DUPLICATE_EMAIL | メールアドレス重複 | 別のメールアドレスを使用してください |

### 422 Unprocessable Entity

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| INVALID_PUNCH_TYPE | 無効な打刻タイプ | IN, OUT, OUTSIDE, RETURNのいずれかを指定してください |
| INVALID_HASH_FORMAT | 無効なハッシュ形式 | SHA-256形式（64文字）で送信してください |
| MISSING_REQUIRED_FIELD | 必須フィールド不足 | 必須パラメータを確認してください |

### 429 Too Many Requests

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| DAILY_LIMIT_EXCEEDED | 日次制限超過 | 翌日まで待つか、管理者に連絡してください |
| RATE_LIMIT_EXCEEDED | レート制限超過 | しばらく待ってから再試行してください |

### 500 Internal Server Error

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| INTERNAL_ERROR | 内部エラー | システム管理者に連絡してください |
| DATABASE_ERROR | データベースエラー | しばらく待ってから再試行してください |

### 503 Service Unavailable

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| PASORI_CONNECTION_ERROR | PaSoRi接続エラー | カードリーダーの接続を確認してください |
| SERVICE_UNAVAILABLE | サービス利用不可 | メンテナンス情報を確認してください |

### 507 Insufficient Storage

| エラーコード | 説明 | 対処方法 |
|-------------|------|----------|
| OFFLINE_QUEUE_FULL | オフラインキュー満杯 | ネットワーク復旧を待つか、管理者に連絡してください |

## 打刻関連エラー詳細

### 重複打刻エラー

```json
{
  "error": {
    "error": "DUPLICATE_PUNCH",
    "message": "重複打刻エラー: 3分以内に既に打刻があります",
    "details": {
      "last_punch_time": "2023-12-01T09:00:00+09:00",
      "wait_seconds": 120
    }
  }
}
```

### 日次制限エラー

```json
{
  "error": {
    "error": "DAILY_LIMIT_EXCEEDED",
    "message": "日次制限エラー: 外出は1日3回までです（現在3回）",
    "details": {
      "punch_type": "OUTSIDE",
      "current_count": 3,
      "daily_limit": 3
    }
  }
}
```

### 打刻順序エラー

```json
{
  "error": {
    "error": "INVALID_SEQUENCE",
    "message": "現在の状態（外出中）では戻りはできません",
    "details": {
      "current_status": "外出中",
      "attempted_punch": "RETURN",
      "allowed_punches": ["OUTSIDE"]
    }
  }
}
```

## セキュリティ関連エラー

### SQLインジェクション検出

```json
{
  "error": {
    "error": "SECURITY_VIOLATION",
    "message": "危険な入力が検出されました",
    "incident_id": "SEC-2023-12-01-001"
  }
}
```

### レート制限

```json
{
  "error": {
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "アクセス回数が制限を超えました",
    "retry_after": 300,
    "limit": "10 requests per minute"
  }
}
```

## エラー対応フローチャート

```
エラー発生
    │
    ├─ 4xx系エラー
    │   ├─ 400: パラメータを確認
    │   ├─ 404: リソースの存在を確認
    │   ├─ 409: 競合状態を解決
    │   └─ 429: 制限解除を待つ
    │
    └─ 5xx系エラー
        ├─ 500: ログを確認、管理者に連絡
        ├─ 503: サービス状態を確認
        └─ 507: ストレージ容量を確認
```

## トラブルシューティング

### よくあるエラーと解決方法

1. **「未登録のカード」エラー**
   - カードが従業員に紐付けられているか確認
   - カードのIDmハッシュが正しいか確認
   - 従業員がアクティブ状態か確認

2. **「重複打刻」エラー**
   - 前回の打刻から3分以上経過しているか確認
   - システム時刻のずれがないか確認

3. **「PaSoRi接続エラー」**
   - USBケーブルの接続を確認
   - ドライバーのインストール状態を確認
   - 他のアプリケーションがPaSoRiを使用していないか確認

4. **「オフラインキュー満杯」エラー**
   - ネットワーク接続を確認
   - オフライン打刻の同期状態を確認
   - 必要に応じて古いデータを手動削除

## ログ確認方法

エラーの詳細はログファイルで確認できます：

```bash
# エラーログ
tail -f logs/error.log

# セキュリティ監査ログ
tail -f logs/security_audit.log

# 打刻専用ログ
tail -f logs/punch.log
```

## サポート連絡先

解決できない問題が発生した場合は、以下の情報と共にサポートに連絡してください：

- エラーコード
- エラーメッセージ
- 発生日時
- 従業員ID（可能な場合）
- 実行した操作の詳細

サポートメール: support@attendance-system.example.com