# 勤怠管理システム Makefile

.PHONY: help setup install clean run dev test test-cov lint format check security db-init db-migrate db-revision docs hardware-test doctor

# デフォルトターゲット
.DEFAULT_GOAL := help

# 変数定義
PYTHON := python3
PIP := pip3
VENV := venv
BACKEND_DIR := backend
APP_MODULE := backend.app.main:app
TEST_DIR := tests

# ヘルプ
help: ## ヘルプを表示
	@echo "勤怠管理システム - 開発コマンド一覧"
	@echo ""
	@echo "使用方法: make [ターゲット]"
	@echo ""
	@echo "セットアップ:"
	@grep -E '^(setup|install|clean):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""
	@echo "開発:"
	@grep -E '^(run|dev|test|test-cov):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""
	@echo "コード品質:"
	@grep -E '^(lint|format|check|security):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""
	@echo "データベース:"
	@grep -E '^(db-init|db-migrate|db-revision):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""
	@echo "その他:"
	@grep -E '^(docs|hardware-test|doctor):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# セットアップ
setup: ## 開発環境を完全セットアップ
	@echo "🚀 開発環境のセットアップを開始します..."
	@bash setup.sh

install: ## 依存関係をインストール
	@echo "📦 依存関係をインストールしています..."
	@if [ -d "$(VENV)" ]; then \
		. $(VENV)/bin/activate && $(PIP) install -r requirements.txt; \
	else \
		$(PIP) install -r requirements.txt; \
	fi
	@echo "✅ インストール完了"

clean: ## 生成ファイルをクリーンアップ
	@echo "🧹 クリーンアップ中..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ クリーンアップ完了"

# 開発
run: ## アプリケーションを起動
	@echo "🚀 アプリケーションを起動しています..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000

dev: ## 開発モード（自動リロード）で起動
	@echo "🔧 開発モードで起動しています..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test: ## テストを実行
	@echo "🧪 テストを実行しています..."
	@$(PYTHON) -m pytest $(TEST_DIR) -v

test-cov: ## カバレッジ付きでテストを実行
	@echo "🧪 カバレッジ測定付きでテストを実行しています..."
	@$(PYTHON) -m pytest $(TEST_DIR) -v --cov=backend --cov-report=html --cov-report=term

# コード品質
lint: ## コードをリント（flake8）
	@echo "🔍 コードをチェックしています..."
	@$(PYTHON) -m flake8 $(BACKEND_DIR) $(TEST_DIR) hardware

format: ## コードをフォーマット（black）
	@echo "✨ コードをフォーマットしています..."
	@$(PYTHON) -m black $(BACKEND_DIR) $(TEST_DIR) hardware

check: ## 型チェック（mypy）
	@echo "🔍 型チェックを実行しています..."
	@$(PYTHON) -m mypy $(BACKEND_DIR) --ignore-missing-imports

security: ## セキュリティチェック（bandit）
	@echo "🔒 セキュリティチェックを実行しています..."
	@$(PYTHON) -m pip install bandit 2>/dev/null || true
	@$(PYTHON) -m bandit -r $(BACKEND_DIR) -ll

# データベース
db-init: ## データベースを初期化
	@echo "🗄️  データベースを初期化しています..."
	@$(PYTHON) -c "from backend.app.database import init_db; init_db()"

db-migrate: ## データベースマイグレーションを実行
	@echo "🗄️  マイグレーションを実行しています..."
	@cd $(BACKEND_DIR) && alembic upgrade head

db-revision: ## 新しいマイグレーションを作成
	@echo "🗄️  新しいマイグレーションを作成しています..."
	@read -p "マイグレーション名を入力: " name; \
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$$name"

# その他
docs: ## APIドキュメントを開く
	@echo "📚 APIドキュメントを開いています..."
	@python -m webbrowser http://localhost:8000/docs

hardware-test: ## PaSoRiハードウェアテストを実行
	@echo "🔧 PaSoRiテストを実行しています..."
	@$(PYTHON) hardware/pasori_test.py

doctor: ## 環境診断を実行
	@echo "🏥 環境診断を実行しています..."
	@echo ""
	@echo "Python バージョン:"
	@$(PYTHON) --version
	@echo ""
	@echo "pip バージョン:"
	@$(PIP) --version
	@echo ""
	@echo "インストール済みパッケージ:"
	@$(PIP) list | grep -E "(fastapi|uvicorn|sqlalchemy|nfcpy)"
	@echo ""
	@echo "データベースファイル:"
	@ls -la data/*.db 2>/dev/null || echo "  データベースファイルが見つかりません"
	@echo ""
	@echo "環境変数ファイル:"
	@ls -la .env 2>/dev/null || echo "  .envファイルが見つかりません（.env.exampleを参考に作成してください）"
	@echo ""
	@echo "✅ 診断完了"