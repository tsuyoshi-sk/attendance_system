#!/bin/bash
# 最小動作確認シナリオ（Smoke Test）
# attendance_system の基本的な動作を一気通しで確認するスクリプト

set -e  # エラー発生時に即座に終了

# 色付きログ出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# プロジェクトルートディレクトリに移動
cd "$(dirname "$0")/.." || exit 1

log_info "Smoke Test開始"
log_info "作業ディレクトリ: $(pwd)"

# ===== 環境変数の設定 =====
log_info "環境変数の設定を確認中..."

if [ ! -f ".env" ]; then
    log_warn ".env ファイルが存在しません。.env.exampleからコピーします..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_info ".env ファイルを作成しました"
    else
        log_error ".env.example が見つかりません"
        exit 1
    fi
fi

# DATABASE_URLを確認・設定
if ! grep -q "^DATABASE_URL=" .env; then
    log_info "DATABASE_URLを設定します..."
    echo "DATABASE_URL=sqlite:///data/attendance.db" >> .env
fi

# dataディレクトリの作成
mkdir -p data
log_info "データディレクトリを確認/作成しました: data/"

# ===== データベースマイグレーション =====
log_info "データベースマイグレーションを実行中..."

if [ -f "data/attendance.db" ]; then
    log_warn "既存のattendance.dbが存在します。バックアップします..."
    mv data/attendance.db "data/attendance.db.backup.$(date +%Y%m%d%H%M%S)"
fi

if command -v alembic &> /dev/null; then
    alembic upgrade head
    log_info "マイグレーション完了"
else
    log_warn "alembicが見つかりません。Pythonから直接データベースを初期化します..."
    python -c "from backend.app.database import Base, engine; Base.metadata.create_all(bind=engine); print('Database initialized')"
fi

# ===== 初期管理者ユーザーの作成 =====
log_info "初期管理者ユーザーを作成中..."

python << 'PYTHON_SCRIPT'
from backend.app.database import SessionLocal
from backend.app.models import User, UserRole, Department
from backend.app.services.auth_service import AuthService
from datetime import datetime

db = SessionLocal()
try:
    # デフォルト部署
    dept = Department(
        name='総務部',
        code='SOMU',
        description='総務部',
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(dept)
    db.flush()

    # 管理者ユーザー
    service = AuthService(db)
    password_hash = service.get_password_hash('admin123!')

    admin = User(
        username='admin',
        password_hash=password_hash,
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(admin)
    db.commit()
    print("✓ 管理者ユーザー作成完了 (username: admin, password: admin123!)")
except Exception as e:
    print(f"管理者ユーザー作成エラー: {e}")
    db.rollback()
finally:
    db.close()
PYTHON_SCRIPT

# ===== APIサーバー起動確認 =====
log_info "APIサーバーが起動しているか確認中..."

API_BASE="http://localhost:8080"

if ! curl -s -f "${API_BASE}/health" > /dev/null; then
    log_error "APIサーバーが起動していません。"
    log_error "別のターミナルで以下を実行してください:"
    log_error "  uvicorn backend.app.main:app --host 0.0.0.0 --port 8080"
    exit 1
fi

log_info "APIサーバー起動確認完了"

# ===== ログイン =====
log_info "管理者でログイン中..."

TOKEN=$(curl -s -X POST "${API_BASE}/api/v1/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=admin' \
  --data-urlencode 'password=admin123!' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    log_error "ログインに失敗しました"
    exit 1
fi

log_info "ログイン成功。トークン: ${TOKEN:0:30}..."
AUTH_HEADER="Authorization: Bearer $TOKEN"

# ===== 従業員作成 =====
log_info "テスト従業員を作成中..."

EMPLOYEE_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/admin/employees" \
  -H "$AUTH_HEADER" \
  -H 'Content-Type: application/json' \
  -d '{
    "employee_code": "SMOKE001",
    "name": "スモークテスト太郎",
    "email": "smoke.test@example.com",
    "department": "テスト部",
    "wage_type": "monthly",
    "monthly_salary": 300000,
    "is_active": true
  }')

EMPLOYEE_ID=$(echo "$EMPLOYEE_RESPONSE" | jq -r '.id')

if [ -z "$EMPLOYEE_ID" ] || [ "$EMPLOYEE_ID" = "null" ]; then
    log_error "従業員作成に失敗しました"
    echo "$EMPLOYEE_RESPONSE" | jq '.'
    exit 1
fi

log_info "従業員作成成功。ID: $EMPLOYEE_ID"

# 従業員に card_idm_hash を設定
log_info "従業員にカードを登録中..."

python << PYTHON_SCRIPT
import hashlib
from config.config import config
from backend.app.database import SessionLocal
from backend.app.models import Employee

card_idm = '0123456789abcdef'
card_idm_hash = hashlib.sha256(f'{card_idm}{config.IDM_HASH_SECRET}'.encode()).hexdigest()

db = SessionLocal()
try:
    employee = db.query(Employee).filter(Employee.id == $EMPLOYEE_ID).first()
    if employee:
        employee.card_idm_hash = card_idm_hash
        db.commit()
        print(f"✓ カード登録完了 (IDm: {card_idm}, Hash: {card_idm_hash})")
    else:
        print("従業員が見つかりません")
except Exception as e:
    print(f"カード登録エラー: {e}")
    db.rollback()
finally:
    db.close()
PYTHON_SCRIPT

# ===== 打刻テスト (4種類) =====
log_info "打刻テスト開始..."

CARD_IDM="0123456789abcdef"

# 1. 出勤 (IN)
log_info "1. 出勤打刻..."
PUNCH_IN=$(curl -s -X POST "${API_BASE}/api/v1/punch/" \
  -H "$AUTH_HEADER" \
  -H 'Content-Type: application/json' \
  -d "{\"card_idm\":\"$CARD_IDM\",\"punch_type\":\"in\"}")

if echo "$PUNCH_IN" | jq -e '.success' > /dev/null; then
    log_info "  ✓ 出勤: $(echo "$PUNCH_IN" | jq -r '.message')"
else
    log_error "  ✗ 出勤失敗"
    echo "$PUNCH_IN" | jq '.'
    exit 1
fi

# 2. 外出 (OUTSIDE)
log_info "2. 外出打刻..."
PUNCH_OUTSIDE=$(curl -s -X POST "${API_BASE}/api/v1/punch/" \
  -H "$AUTH_HEADER" \
  -H 'Content-Type: application/json' \
  -d "{\"card_idm\":\"$CARD_IDM\",\"punch_type\":\"outside\"}")

if echo "$PUNCH_OUTSIDE" | jq -e '.success' > /dev/null; then
    log_info "  ✓ 外出: $(echo "$PUNCH_OUTSIDE" | jq -r '.message')"
else
    log_error "  ✗ 外出失敗"
    echo "$PUNCH_OUTSIDE" | jq '.'
    exit 1
fi

# 3. 戻り (RETURN)
log_info "3. 戻り打刻..."
PUNCH_RETURN=$(curl -s -X POST "${API_BASE}/api/v1/punch/" \
  -H "$AUTH_HEADER" \
  -H 'Content-Type: application/json' \
  -d "{\"card_idm\":\"$CARD_IDM\",\"punch_type\":\"return\"}")

if echo "$PUNCH_RETURN" | jq -e '.success' > /dev/null; then
    log_info "  ✓ 戻り: $(echo "$PUNCH_RETURN" | jq -r '.message')"
else
    log_error "  ✗ 戻り失敗"
    echo "$PUNCH_RETURN" | jq '.'
    exit 1
fi

# 4. 退勤 (OUT)
log_info "4. 退勤打刻..."
PUNCH_OUT=$(curl -s -X POST "${API_BASE}/api/v1/punch/" \
  -H "$AUTH_HEADER" \
  -H 'Content-Type: application/json' \
  -d "{\"card_idm\":\"$CARD_IDM\",\"punch_type\":\"out\"}")

if echo "$PUNCH_OUT" | jq -e '.success' > /dev/null; then
    log_info "  ✓ 退勤: $(echo "$PUNCH_OUT" | jq -r '.message')"
else
    log_error "  ✗ 退勤失敗"
    echo "$PUNCH_OUT" | jq '.'
    exit 1
fi

# ===== 日次レポート取得 =====
log_info "日次レポート取得中..."

TODAY=$(date +%Y-%m-%d)
DAILY_REPORT=$(curl -s -X GET "${API_BASE}/api/v1/reports/daily/${TODAY}" \
  -H "$AUTH_HEADER")

REPORT_COUNT=$(echo "$DAILY_REPORT" | jq 'length')
log_info "日次レポート取得成功: ${REPORT_COUNT}件"

# ===== 月次レポート取得 =====
log_info "月次レポート取得中..."

YEAR=$(date +%Y)
MONTH=$(date +%-m)
MONTHLY_REPORT=$(curl -s -X GET "${API_BASE}/api/v1/reports/monthly/${YEAR}/${MONTH}" \
  -H "$AUTH_HEADER")

MONTHLY_COUNT=$(echo "$MONTHLY_REPORT" | jq 'length')
log_info "月次レポート取得成功: ${MONTHLY_COUNT}件"

# ===== CSV エクスポート =====
log_info "CSV エクスポートテスト中..."

CSV_FILE="/tmp/smoke_test_daily_${TODAY}.csv"
curl -s -X GET "${API_BASE}/api/v1/reports/export/daily/csv?date=${TODAY}" \
  -H "$AUTH_HEADER" \
  -o "$CSV_FILE"

if [ -f "$CSV_FILE" ] && [ -s "$CSV_FILE" ]; then
    CSV_LINES=$(wc -l < "$CSV_FILE")
    log_info "CSV エクスポート成功: ${CSV_LINES}行 (ファイル: $CSV_FILE)"
else
    log_error "CSV エクスポート失敗"
    exit 1
fi

# ===== 完了 =====
echo ""
log_info "========================================="
log_info "Smoke Test 完了"
log_info "========================================="
log_info "✓ データベース初期化"
log_info "✓ 管理者ユーザー作成"
log_info "✓ ログイン"
log_info "✓ 従業員作成"
log_info "✓ 打刻 4種類 (IN/OUTSIDE/RETURN/OUT)"
log_info "✓ 日次レポート取得"
log_info "✓ 月次レポート取得"
log_info "✓ CSV エクスポート"
log_info "========================================="
echo ""
log_info "すべてのテストが正常に完了しました！"

exit 0
