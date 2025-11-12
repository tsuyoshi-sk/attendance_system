#!/bin/bash
# 勤怠管理システム統合版デプロイスクリプト
# =====================================

set -e  # エラー時に停止

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env.integrated"
BACKUP_DIR="${PROJECT_ROOT}/data/backups"
LOG_FILE="${PROJECT_ROOT}/logs/deployment_$(date +%Y%m%d_%H%M%S).log"

# ログ出力関数
log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

# 事前チェック
pre_check() {
    log "=== 事前チェック開始 ==="
    
    # Python確認
    if ! command -v python3 &> /dev/null; then
        log_error "Python3がインストールされていません"
        exit 1
    fi
    
    # 必要なディレクトリ作成
    mkdir -p "${PROJECT_ROOT}/data"
    mkdir -p "${PROJECT_ROOT}/logs"
    mkdir -p "${PROJECT_ROOT}/data/exports"
    mkdir -p "${PROJECT_ROOT}/data/backups"
    
    log_success "事前チェック完了"
}

# 環境設定
setup_environment() {
    log "\n=== 環境設定 ==="
    
    # .env.integratedを.envにコピー
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "${PROJECT_ROOT}/.env"
        log_success ".env設定ファイルを配置しました"
    else
        log_error ".env.integratedファイルが見つかりません"
        exit 1
    fi
    
    # 仮想環境の確認・作成
    if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
        log "仮想環境を作成しています..."
        python3 -m venv "${PROJECT_ROOT}/.venv"
        log_success "仮想環境を作成しました"
    fi
    
    # 仮想環境の有効化
    source "${PROJECT_ROOT}/.venv/bin/activate"
    log_success "仮想環境を有効化しました"
}

# 依存関係インストール
install_dependencies() {
    log "\n=== 依存関係インストール ==="
    
    # pipのアップグレード
    pip install --upgrade pip
    
    # 依存関係のインストール
    if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
        pip install -r "${PROJECT_ROOT}/requirements.txt"
        log_success "依存関係をインストールしました"
    else
        log_error "requirements.txtが見つかりません"
        exit 1
    fi
}

# データベースバックアップ
backup_database() {
    log "\n=== データベースバックアップ ==="
    
    DB_PATH="${PROJECT_ROOT}/data/attendance_integrated.db"
    if [ -f "$DB_PATH" ]; then
        BACKUP_FILE="${BACKUP_DIR}/attendance_backup_$(date +%Y%m%d_%H%M%S).db"
        cp "$DB_PATH" "$BACKUP_FILE"
        log_success "データベースをバックアップしました: $BACKUP_FILE"
    else
        log_warning "既存のデータベースが見つかりません（新規インストール）"
    fi
}

# データベース初期化
initialize_database() {
    log "\n=== データベース初期化 ==="
    
    # データベースの初期化スクリプト実行
    cd "$PROJECT_ROOT"
    python -c "
from backend.app.database import init_db
from backend.app.services.auth_service import AuthService
from backend.app.database import SessionLocal

print('データベースを初期化しています...')
init_db()

# 初期管理者アカウント作成
db = SessionLocal()
auth_service = AuthService(db)

try:
    # 既存の管理者確認
    from backend.app.models import User
    admin_exists = db.query(User).filter(User.username == 'admin').first()
    
    if not admin_exists:
        admin = auth_service.create_initial_admin(
            username='admin',
            password='admin123456'  # 本番環境では必ず変更してください
        )
        print('初期管理者アカウントを作成しました')
        print('ユーザー名: admin')
        print('パスワード: admin123456 (必ず変更してください)')
    else:
        print('管理者アカウントは既に存在します')
except Exception as e:
    print(f'エラー: {e}')
finally:
    db.close()
"
    
    log_success "データベースを初期化しました"
}

# テスト実行
run_tests() {
    log "\n=== テスト実行 ==="
    
    cd "$PROJECT_ROOT"
    
    # 基本的なimportテスト
    python -c "
try:
    from backend.app.main import app
    from backend.app.api import punch, admin, auth, reports, analytics
    print('✅ モジュールのインポート: 成功')
except Exception as e:
    print(f'❌ モジュールのインポート: 失敗 - {e}')
    exit(1)
"
    
    log_success "基本テスト完了"
}

# サービス起動
start_service() {
    log "\n=== サービス起動 ==="
    
    # 既存のプロセスを停止
    if [ -f "${PROJECT_ROOT}/attendance.pid" ]; then
        OLD_PID=$(cat "${PROJECT_ROOT}/attendance.pid")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill "$OLD_PID"
            log_warning "既存のプロセスを停止しました (PID: $OLD_PID)"
            sleep 2
        fi
    fi
    
    # 本番モードかどうか確認
    read -p "本番モードで起動しますか？ (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 本番モード起動
        log "本番モードで起動しています..."
        cd "$PROJECT_ROOT"
        nohup uvicorn backend.app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --workers 4 \
            --log-level info \
            > "${PROJECT_ROOT}/logs/attendance.log" 2>&1 &
        
        echo $! > "${PROJECT_ROOT}/attendance.pid"
        log_success "本番モードでサービスを起動しました (PID: $(cat ${PROJECT_ROOT}/attendance.pid))"
    else
        # 開発モード起動
        log "開発モードで起動しています..."
        cd "$PROJECT_ROOT"
        uvicorn backend.app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --reload \
            --log-level debug
    fi
}

# ヘルスチェック
health_check() {
    log "\n=== ヘルスチェック ==="
    
    sleep 3  # サービス起動待機
    
    # 基本ヘルスチェック
    if curl -s "http://localhost:8000/health" > /dev/null; then
        log_success "基本ヘルスチェック: 成功"
    else
        log_error "基本ヘルスチェック: 失敗"
        return 1
    fi
    
    # 統合ヘルスチェック
    HEALTH_RESPONSE=$(curl -s "http://localhost:8000/health/integrated")
    if [ $? -eq 0 ]; then
        log_success "統合ヘルスチェック: 成功"
        log "ヘルスチェック結果:"
        echo "$HEALTH_RESPONSE" | python -m json.tool | tee -a "$LOG_FILE"
    else
        log_error "統合ヘルスチェック: 失敗"
        return 1
    fi
}

# デプロイ後の情報表示
show_deployment_info() {
    log "\n${GREEN}=== デプロイ完了 ===${NC}"
    log ""
    log "📍 アクセスURL:"
    log "   - API: http://localhost:8000"
    log "   - ドキュメント: http://localhost:8000/docs"
    log "   - 統合ヘルスチェック: http://localhost:8000/health/integrated"
    log ""
    log "🔑 初期管理者アカウント:"
    log "   - ユーザー名: admin"
    log "   - パスワード: admin123456 (必ず変更してください)"
    log ""
    log "📝 次のステップ:"
    log "   1. 管理者パスワードを変更"
    log "   2. 従業員情報を登録"
    log "   3. PaSoRiデバイスを接続（本番環境）"
    log "   4. システム監視を設定"
    log ""
    log "ログファイル: $LOG_FILE"
}

# メイン処理
main() {
    log "${GREEN}勤怠管理システム統合版 デプロイスクリプト${NC}"
    log "開始時刻: $(date)"
    log "======================================"
    
    pre_check
    setup_environment
    install_dependencies
    backup_database
    initialize_database
    run_tests
    start_service
    
    # 本番モードの場合のみヘルスチェック
    if [ -f "${PROJECT_ROOT}/attendance.pid" ]; then
        health_check || log_warning "ヘルスチェックに失敗しました"
    fi
    
    show_deployment_info
    
    log "\n終了時刻: $(date)"
    log "${GREEN}デプロイが完了しました！${NC}"
}

# スクリプト実行
main "$@"
