# 勤怠管理システム開発用Makefile

.PHONY: help dev test lint format clean install validate

# デフォルトターゲット
help: ## ヘルプを表示
	@echo "勤怠管理システム開発コマンド"
	@echo "=========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# 開発環境セットアップ
install: ## 依存関係をインストール
	@echo "📦 依存関係をインストール中..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install; \
	else \
		pip install -r requirements.txt; \
	fi
	@echo "✅ インストール完了"

# 環境設定検証
validate: ## 環境設定を検証
	@echo "🔍 環境設定を検証中..."
	@python scripts/validate_env.py

# 開発サーバー起動
dev: ## 開発サーバーを起動
	@echo "🚀 開発サーバーを起動中..."
	@if [ ! -f ".env" ]; then \
		echo "📋 .envファイルを作成中..."; \
		cp .env.example .env; \
	fi
	@if [ ! -f "attendance.db" ]; then \
		echo "🗄️  データベースを初期化中..."; \
		python scripts/init_database.py; \
	fi
	@echo "✅ http://localhost:8000 で起動中"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000; \
	fi

# テスト実行
test: ## テストを実行
	@echo "🧪 テストを実行中..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pytest tests/ -v; \
	else \
		python -m pytest tests/ -v; \
	fi

# カバレッジ付きテスト
test-cov: ## カバレッジ付きでテストを実行
	@echo "📊 カバレッジ付きテストを実行中..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pytest tests/ -v --cov=backend --cov-report=html --cov-report=term; \
	else \
		python -m pytest tests/ -v --cov=backend --cov-report=html --cov-report=term; \
	fi

# リント実行
lint: ## コード品質チェック
	@echo "🔍 コード品質をチェック中..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run flake8 backend/ tests/ --max-line-length=88 --extend-ignore=E203,W503; \
		poetry run mypy backend/ --ignore-missing-imports; \
	else \
		flake8 backend/ tests/ --max-line-length=88 --extend-ignore=E203,W503; \
		mypy backend/ --ignore-missing-imports; \
	fi

# フォーマット
format: ## コードフォーマット
	@echo "🎨 コードをフォーマット中..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run black backend/ tests/; \
		poetry run isort backend/ tests/; \
	else \
		black backend/ tests/; \
		isort backend/ tests/; \
	fi

# PaSoRiテスト
test-pasori: ## PaSoRi接続テスト
	@echo "🔌 PaSoRi接続をテスト中..."
	@python -m nfc || echo "PaSoRiが見つかりません。モックモードで開発を続けられます。"

# ハードウェアセットアップ（macOS）
setup-mac: ## macOS用PaSoRiセットアップ
	@echo "🍎 macOS用セットアップを実行中..."
	@bash scripts/setup_mac.sh

# データベース初期化
init-db: ## データベースを初期化
	@echo "🗄️  データベースを初期化中..."
	@python scripts/init_database.py

# ログ確認
logs: ## ログを確認
	@echo "📋 ログを表示中..."
	@tail -f logs/*.log 2>/dev/null || echo "ログファイルが見つかりません"

# クリーンアップ
clean: ## 一時ファイルを削除
	@echo "🧹 一時ファイルを削除中..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name ".pytest_cache" -delete
	@find . -type d -name "htmlcov" -delete
	@find . -name "*.log" -delete
	@echo "✅ クリーンアップ完了"

# Docker関連
docker-build: ## Dockerイメージをビルド
	@echo "🐳 Dockerイメージをビルド中..."
	@docker build -t attendance-system .

docker-run: ## Dockerコンテナを起動
	@echo "🚀 Dockerコンテナを起動中..."
	@docker run -p 8000:8000 attendance-system

# 本番デプロイ準備
production-check: ## 本番環境チェック
	@echo "🔍 本番環境の準備状況をチェック中..."
	@python scripts/validate_env.py
	@$(MAKE) test-cov
	@$(MAKE) lint
	@echo "✅ 本番デプロイ準備完了"