# 打刻API仕様書

## 概要

勤怠管理システムの打刻機能に関するAPI仕様書です。PaSoRi RC-S300を使用したFeliCaカード読み取りによる打刻を管理します。

## APIエンドポイント

### 1. 打刻記録作成

従業員の打刻を記録します。

**エンドポイント**: `POST /api/v1/punch/`

**リクエストボディ**:
```json
{
  "employee_id": "string (optional)",
  "punch_type": "IN|OUT|OUTSIDE|RETURN",
  "card_idm": "string (SHA-256ハッシュ化済み, 64文字)",
  "timestamp": "2023-12-01T09:00:00+09:00",
  "device_type": "pasori (default)",
  "location": {
    "latitude": 35.6895,
    "longitude": 139.6917
  },
  "note": "string (optional)"
}
```

**レスポンス (成功: 200 OK)**:
```json
{
  "success": true,
  "message": "出勤を記録しました",
  "timestamp": "2023-12-01T09:00:00+09:00",
  "punch_record": {
    "id": 12345,
    "employee_id": 1,
    "punch_type": "in",
    "punch_time": "2023-12-01T09:00:00+09:00",
    "device_type": "pasori",
    "ip_address": "192.168.1.100",
    "is_offline": false,
    "note": null
  },
  "employee": {
    "id": 1,
    "name": "山田太郎",
    "employee_code": "EMP001"
  }
}
```

**エラーレスポンス**:

- **404 Not Found** - 未登録カード/無効な従業員
```json
{
  "error": {
    "error": "EMPLOYEE_NOT_FOUND",
    "message": "未登録のカード、または無効な従業員です"
  }
}
```

- **409 Conflict** - 重複打刻（3分以内）
```json
{
  "error": {
    "error": "DUPLICATE_PUNCH",
    "message": "重複打刻エラー: 3分以内に既に打刻があります"
  }
}
```

- **429 Too Many Requests** - 日次制限超過
```json
{
  "error": {
    "error": "DAILY_LIMIT_EXCEEDED",
    "message": "日次制限エラー: 外出は1日3回までです（現在3回）"
  }
}
```

- **422 Unprocessable Entity** - バリデーションエラー
```json
{
  "error": {
    "message": "入力データの検証エラー",
    "status_code": 422,
    "details": [
      {
        "loc": ["body", "punch_type"],
        "msg": "打刻種別は ['IN', 'OUT', 'OUTSIDE', 'RETURN'] のいずれかである必要があります",
        "type": "value_error"
      }
    ]
  }
}
```

### 2. 打刻状況取得

従業員の現在の打刻状況を取得します。

**エンドポイント**: `GET /api/v1/punch/status/{employee_id}`

**パスパラメータ**:
- `employee_id` (integer): 従業員ID

**レスポンス (成功: 200 OK)**:
```json
{
  "employee": {
    "id": 1,
    "employee_code": "EMP001",
    "name": "山田太郎",
    "email": "yamada@example.com",
    "department": "営業部",
    "is_active": true
  },
  "current_status": "勤務中",
  "latest_punch": {
    "id": 12345,
    "punch_type": "in",
    "punch_time": "2023-12-01T09:00:00+09:00"
  },
  "today_punches": [
    {
      "id": 12345,
      "punch_type": "in",
      "punch_time": "2023-12-01T09:00:00+09:00"
    }
  ],
  "punch_count": 1,
  "remaining_punches": {
    "in": 0,
    "out": 1,
    "outside": 3,
    "return": 3
  }
}
```

### 3. 打刻履歴取得

従業員の打刻履歴を取得します。

**エンドポイント**: `GET /api/v1/punch/history/{employee_id}`

**パスパラメータ**:
- `employee_id` (integer): 従業員ID

**クエリパラメータ**:
- `date` (string, optional): 対象日（YYYY-MM-DD形式）
- `limit` (integer, optional): 取得件数上限（デフォルト: 10）

**レスポンス (成功: 200 OK)**:
```json
{
  "employee": {
    "id": 1,
    "employee_code": "EMP001",
    "name": "山田太郎"
  },
  "records": [
    {
      "id": 12346,
      "punch_type": "out",
      "punch_time": "2023-12-01T18:00:00+09:00",
      "device_type": "pasori"
    },
    {
      "id": 12345,
      "punch_type": "in",
      "punch_time": "2023-12-01T09:00:00+09:00",
      "device_type": "pasori"
    }
  ],
  "count": 2,
  "filter": {
    "date": "2023-12-01",
    "limit": 10
  }
}
```

### 4. オフラインキュー状態取得

オフラインキューの状態を取得します。

**エンドポイント**: `GET /api/v1/punch/offline/status`

**レスポンス (成功: 200 OK)**:
```json
{
  "status": "online",
  "statistics": {
    "total_pending": 0,
    "failed_records": 0,
    "average_retries": 0.0,
    "oldest_record": null,
    "queue_usage": "0.0%"
  },
  "timestamp": "2023-12-01T12:00:00+09:00"
}
```

## ビジネスルール

### 打刻種別

- **IN** (出勤): 1日1回まで、最初の打刻である必要がある
- **OUT** (退勤): 1日1回まで、勤務中のみ可能
- **OUTSIDE** (外出): 1日3回まで、勤務中のみ可能
- **RETURN** (戻り): 1日3回まで、外出中のみ可能

### 重複打刻防止

同一従業員の3分以内の打刻は拒否されます。

### 深夜勤務対応

- 22:00-05:00の打刻は前日の勤務として処理されます
- ただし、出勤（IN）は常に当日扱いとなります

### 日次制限

- IN/OUT: 各1回まで
- OUTSIDE/RETURN: 各3回まで

## セキュリティ

### IDmハッシュ化

カードIDmは必ずSHA-256でハッシュ化された値を送信してください。

```javascript
// ハッシュ化の例（JavaScript）
const crypto = require('crypto');
const idmHash = crypto.createHash('sha256')
  .update(idm + secretKey)
  .digest('hex');
```

### レート制限

- 同一IPアドレスから: 60秒間に10回まで
- 制限超過時は5分間ブロック

### 入力値検証

- SQLインジェクション対策
- XSS対策
- 入力値長制限

## パフォーマンス要件

- 応答時間: 3秒以内
- 可用性: 99.9%以上
- エラー率: 0.1%以下

## オフライン対応

ネットワーク障害時は自動的にローカルキューに保存され、復旧時に自動同期されます。

- キューサイズ: 最大100件
- 保持期間: 7日間
- 同期失敗時: Slack通知

## エラーコード一覧

| コード | HTTPステータス | 説明 |
|--------|---------------|------|
| EMPLOYEE_NOT_FOUND | 404 | 未登録カードまたは無効な従業員 |
| DUPLICATE_PUNCH | 409 | 3分以内の重複打刻 |
| DAILY_LIMIT_EXCEEDED | 429 | 日次制限超過 |
| VALIDATION_ERROR | 400 | 入力値検証エラー |
| OFFLINE_QUEUE_FULL | 507 | オフラインキュー満杯 |
| INTERNAL_ERROR | 500 | 内部サーバーエラー |

## 使用例

### cURL

```bash
# 打刻記録
curl -X POST "http://localhost:8000/api/v1/punch/" \
  -H "Content-Type: application/json" \
  -d '{
    "punch_type": "IN",
    "card_idm": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "timestamp": "2023-12-01T09:00:00+09:00"
  }'

# 状況確認
curl "http://localhost:8000/api/v1/punch/status/1"

# 履歴取得
curl "http://localhost:8000/api/v1/punch/history/1?date=2023-12-01"
```

### Python

```python
import requests
import hashlib
from datetime import datetime

# IDmハッシュ化
idm = "0123456789ABCDEF"
secret_key = "your_secret_key"
idm_hash = hashlib.sha256(f"{idm}{secret_key}".encode()).hexdigest()

# 打刻記録
response = requests.post(
    "http://localhost:8000/api/v1/punch/",
    json={
        "punch_type": "IN",
        "card_idm": idm_hash,
        "timestamp": datetime.now().isoformat()
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"打刻成功: {data['message']}")
else:
    error = response.json()
    print(f"エラー: {error['error']['message']}")
```