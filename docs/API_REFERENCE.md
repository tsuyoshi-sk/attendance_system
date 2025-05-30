# 勤怠管理システム統合版 API リファレンス

## 概要

勤怠管理システム統合版は、PaSoRi RC-S380/RC-S300を使用したICカード打刻、従業員管理、レポート生成、分析機能を提供するRESTful APIです。

### ベースURL
```
http://localhost:8000/api/v1
```

### 認証
多くのエンドポイントはJWT (JSON Web Token) による認証が必要です。
ログイン後に取得したトークンを、Authorizationヘッダーに設定してください。

```
Authorization: Bearer <your-token-here>
```

## 目次

1. [認証 API](#認証-api)
2. [打刻 API](#打刻-api)
3. [管理 API](#管理-api)
4. [レポート API](#レポート-api)
5. [分析 API](#分析-api)
6. [システム API](#システム-api)

---

## 認証 API

### ログイン
管理者または従業員としてログインし、アクセストークンを取得します。

**エンドポイント:** `POST /auth/login`

**リクエストボディ:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**レスポンス:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "is_admin": true,
    "employee_id": null
  }
}
```

### 現在のユーザー情報取得
**エンドポイント:** `GET /auth/me`

**認証:** 必要

**レスポンス:**
```json
{
  "id": 1,
  "username": "admin",
  "is_admin": true,
  "is_active": true,
  "employee": null,
  "permissions": ["employee_manage", "report_view", "system_admin"]
}
```

### パスワード変更
**エンドポイント:** `POST /auth/change-password`

**認証:** 必要

**リクエストボディ:**
```json
{
  "current_password": "old_password",
  "new_password": "new_secure_password"
}
```

---

## 打刻 API

### 打刻実行
ICカードを使用して出勤・退勤を記録します。

**エンドポイント:** `POST /punch`

**リクエストボディ:**
```json
{
  "card_idm": "0123456789ABCDEF",
  "punch_type": "IN"
}
```

**パラメータ:**
- `card_idm`: カードのIDm（16進数文字列）
- `punch_type`: 打刻種別（IN: 出勤, OUT: 退勤）

**レスポンス:**
```json
{
  "success": true,
  "message": "出勤打刻を記録しました",
  "timestamp": "2025-01-25T09:00:00",
  "punch_record": {
    "id": 123,
    "employee_id": 1,
    "punch_type": "IN",
    "punch_time": "2025-01-25T09:00:00",
    "device_type": "pasori"
  },
  "employee": {
    "id": 1,
    "name": "山田太郎",
    "department": "開発部"
  }
}
```

### 打刻状態確認
従業員の現在の勤務状態を確認します。

**エンドポイント:** `GET /punch/status/{employee_id}`

**レスポンス:**
```json
{
  "employee_id": 1,
  "is_working": true,
  "last_punch_type": "IN",
  "last_punch_time": "2025-01-25T09:00:00",
  "today_work_hours": 4.5
}
```

### 打刻履歴取得
**エンドポイント:** `GET /punch/history/{employee_id}`

**クエリパラメータ:**
- `start_date`: 開始日（YYYY-MM-DD）
- `end_date`: 終了日（YYYY-MM-DD）
- `limit`: 取得件数（デフォルト: 100）

---

## 管理 API

### 従業員一覧取得
**エンドポイント:** `GET /admin/employees`

**認証:** 必要（管理者権限）

**クエリパラメータ:**
- `skip`: スキップ件数（ページネーション）
- `limit`: 取得件数（最大100）
- `is_active`: 有効フラグフィルター
- `department`: 部署フィルター
- `search`: 検索文字列（名前、コード、メール）

**レスポンス:**
```json
{
  "total": 50,
  "employees": [
    {
      "id": 1,
      "employee_code": "EMP001",
      "name": "山田太郎",
      "name_kana": "ヤマダタロウ",
      "email": "yamada@example.com",
      "department": "開発部",
      "position": "エンジニア",
      "employment_type": "正社員",
      "hire_date": "2023-04-01",
      "wage_type": "monthly",
      "monthly_salary": 300000,
      "is_active": true,
      "has_card": true
    }
  ]
}
```

### 従業員登録
**エンドポイント:** `POST /admin/employees`

**認証:** 必要（管理者権限）

**リクエストボディ:**
```json
{
  "employee_code": "EMP002",
  "name": "鈴木花子",
  "name_kana": "スズキハナコ",
  "email": "suzuki@example.com",
  "department": "営業部",
  "position": "主任",
  "employment_type": "正社員",
  "hire_date": "2024-01-01",
  "wage_type": "hourly",
  "hourly_rate": "2500.00",
  "is_active": true
}
```

### カード登録
**エンドポイント:** `POST /admin/employees/{employee_id}/cards`

**認証:** 必要（管理者権限）

**リクエストボディ:**
```json
{
  "card_idm_hash": "sha256_hashed_idm",
  "card_name": "メインカード"
}
```

---

## レポート API

### 日次レポート生成
**エンドポイント:** `POST /reports/daily`

**認証:** 必要

**リクエストボディ:**
```json
{
  "target_date": "2025-01-25"
}
```

### 日次レポート取得
**エンドポイント:** `GET /reports/daily/{target_date}`

**認証:** 必要

**レスポンス:**
```json
{
  "date": "2025-01-25",
  "total_employees": 50,
  "worked_employees": 45,
  "summaries": [
    {
      "employee_id": 1,
      "employee_name": "山田太郎",
      "department": "開発部",
      "punch_in_time": "09:00:00",
      "punch_out_time": "18:30:00",
      "break_hours": 1.0,
      "work_hours": 8.5,
      "overtime_hours": 0.5,
      "is_holiday": false,
      "daily_wage": 25000
    }
  ]
}
```

### 月次レポート取得
**エンドポイント:** `GET /reports/monthly/{year}/{month}`

**認証:** 必要

**レスポンス:**
```json
{
  "year": 2025,
  "month": 1,
  "summaries": [
    {
      "employee_id": 1,
      "employee_name": "山田太郎",
      "work_days": 20,
      "total_work_hours": 170.0,
      "total_overtime_hours": 10.0,
      "total_night_hours": 0.0,
      "total_holiday_hours": 0.0,
      "total_wage": 325000,
      "details": {
        "base_wage": 300000,
        "overtime_wage": 25000,
        "night_wage": 0,
        "holiday_wage": 0
      }
    }
  ]
}
```

### CSV出力
**エンドポイント:** `GET /reports/export/monthly/csv`

**認証:** 必要

**クエリパラメータ:**
- `year`: 年
- `month`: 月

**レスポンス:** CSV ファイル（Content-Type: text/csv）

---

## 分析 API

### ダッシュボード取得
**エンドポイント:** `GET /analytics/dashboard`

**認証:** 必要

**レスポンス:**
```json
{
  "overview": {
    "total_employees": 50,
    "active_today": 45,
    "on_leave": 3,
    "late_arrivals": 2
  },
  "attendance_rate": {
    "today": 94.0,
    "this_week": 92.5,
    "this_month": 93.2
  },
  "work_hours": {
    "average_daily": 8.2,
    "total_overtime_this_month": 150.5
  },
  "alerts": [
    {
      "type": "overtime",
      "message": "今月の残業時間が40時間を超えている従業員: 3名",
      "severity": "warning"
    }
  ]
}
```

### 勤務時間推移取得
**エンドポイント:** `GET /analytics/charts/work-hours-trend`

**認証:** 必要

**クエリパラメータ:**
- `period`: 期間（week, month, quarter, year）
- `employee_id`: 従業員ID（省略時は全体）

---

## システム API

### ヘルスチェック
**エンドポイント:** `GET /health`

**レスポンス:**
```json
{
  "status": "healthy",
  "name": "勤怠管理システム統合版",
  "version": "1.0.0",
  "database": "connected",
  "pasori": "ready"
}
```

### 統合ヘルスチェック
**エンドポイント:** `GET /health/integrated`

**レスポンス:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-25T10:00:00",
  "duration_seconds": 0.5,
  "subsystems": [
    {
      "name": "database",
      "status": "healthy",
      "message": "データベース正常",
      "details": {
        "tables": 8,
        "employees": 50,
        "punch_records": 12500
      }
    },
    {
      "name": "punch_system",
      "status": "healthy",
      "message": "打刻システム正常",
      "details": {
        "last_punch": "2025-01-25T09:58:00",
        "today_count": 89
      }
    }
  ],
  "summary": {
    "total": 7,
    "healthy": 7,
    "degraded": 0,
    "unhealthy": 0
  }
}
```

### システム情報
**エンドポイント:** `GET /info`

**レスポンス:**
```json
{
  "app": {
    "name": "勤怠管理システム統合版",
    "version": "1.0.0",
    "debug": false
  },
  "features": {
    "slack_notification": false,
    "pasori_mock_mode": true
  },
  "settings": {
    "business_hours": {
      "start": "09:00:00",
      "end": "18:00:00"
    },
    "overtime_rates": {
      "normal": 1.25,
      "late": 1.5,
      "night": 1.25,
      "holiday": 1.35
    }
  }
}
```

---

## エラーレスポンス

すべてのAPIは、エラー時に以下の形式でレスポンスを返します：

```json
{
  "error": {
    "message": "エラーの詳細メッセージ",
    "status_code": 400,
    "details": [
      {
        "field": "employee_code",
        "message": "このフィールドは必須です"
      }
    ]
  }
}
```

### HTTPステータスコード

- `200 OK`: 成功
- `201 Created`: リソース作成成功
- `400 Bad Request`: リクエストエラー
- `401 Unauthorized`: 認証エラー
- `403 Forbidden`: 権限エラー
- `404 Not Found`: リソースが見つからない
- `422 Unprocessable Entity`: バリデーションエラー
- `500 Internal Server Error`: サーバーエラー

---

## 開発者向け情報

### API ドキュメント（Swagger UI）
開発環境では、以下のURLでインタラクティブなAPIドキュメントを利用できます：
```
http://localhost:8000/docs
```

### 代替ドキュメント（ReDoc）
```
http://localhost:8000/redoc
```

### OpenAPI スキーマ
```
http://localhost:8000/openapi.json
```