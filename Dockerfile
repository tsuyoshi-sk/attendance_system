# マルチステージビルドを使用して軽量なイメージを作成
FROM python:3.12-slim as builder

# 作業ディレクトリの設定
WORKDIR /app

# システムパッケージの更新とビルドツールのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルのコピー
COPY requirements.txt .

# Pythonパッケージのインストール（wheelファイルの作成）
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# 実行用の軽量イメージ
FROM python:3.12-slim

# 作業ディレクトリの設定
WORKDIR /app

# 実行時に必要なシステムパッケージのインストール
RUN apt-get update && apt-get install -y \
    libpq5 \
    libusb-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 非rootユーザーの作成
RUN useradd -m -u 1000 attendance && \
    mkdir -p /app/logs /app/data /app/exports && \
    chown -R attendance:attendance /app

# ビルドステージからwheelファイルをコピー
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Pythonパッケージのインストール
RUN pip install --no-cache /wheels/*

# アプリケーションコードのコピー
COPY --chown=attendance:attendance . .

# 環境変数の設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# 非rootユーザーに切り替え
USER attendance

# ヘルスチェックの設定
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# ポートの公開
EXPOSE 8000

# アプリケーションの起動
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]