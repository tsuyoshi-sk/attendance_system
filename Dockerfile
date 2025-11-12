# マルチステージビルドを使用して軽量なイメージを作成
# ステージ1: 依存関係のビルド
FROM python:3.11-slim-bullseye as builder

# 作業ディレクトリの設定
WORKDIR /app

# システムパッケージの更新とビルドツールのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルのコピー
COPY requirements.txt .

# Pythonパッケージのインストール（wheelファイルの作成）
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ステージ2: 実行用の軽量イメージ
FROM python:3.11-slim-bullseye

# 作業ディレクトリの設定
WORKDIR /app

# 実行時に必要なシステムパッケージのみインストール
RUN apt-get update && apt-get install -y \
    libpq5 \
    libusb-1.0-0 \
    curl \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 非rootユーザーの作成
RUN groupadd -g 1000 attendance && \
    useradd -m -u 1000 -g attendance attendance && \
    mkdir -p /app/logs /app/data /app/exports /app/offline_queue && \
    chown -R attendance:attendance /app

# ビルドステージからwheelファイルをコピー
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Pythonパッケージのインストール
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# アプリケーションコードのコピー（必要なファイルのみ）
COPY --chown=attendance:attendance backend ./backend
COPY --chown=attendance:attendance config ./config
COPY --chown=attendance:attendance src ./src
COPY --chown=attendance:attendance alembic.ini ./
COPY --chown=attendance:attendance alembic ./alembic

# スタティックファイルのコピー（存在する場合）
COPY --chown=attendance:attendance pwa/dist ./static

# 環境変数の設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# 非rootユーザーに切り替え
USER attendance

# ヘルスチェックの設定（curlを使用）
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ポートの公開
EXPOSE 8000

# エントリーポイントスクリプトの作成
RUN echo '#!/bin/sh\n\
set -e\n\
echo "Starting attendance system..."\n\
# データベースマイグレーション（本番環境では別途実行を推奨）\n\
if [ "$RUN_MIGRATIONS" = "true" ]; then\n\
    echo "Running database migrations..."\n\
    alembic upgrade head || echo "Migration failed, continuing..."\n\
fi\n\
# アプリケーションの起動\n\
exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# アプリケーションの起動
ENTRYPOINT ["/app/entrypoint.sh"]