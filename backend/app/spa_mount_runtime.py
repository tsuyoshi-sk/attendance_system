"""
SPA統合ランタイム - FastAPIアプリに静的ファイル配信とフォールバックを追加
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


def apply_spa_mount(app: FastAPI) -> None:
    """
    FastAPIアプリにSPA統合を適用

    - /assetsへの静的ファイル配信
    - APIルート以外のすべてのパスでindex.htmlを返す（SPA用）
    """
    static_dir = Path(__file__).parent / "static"

    if not static_dir.exists():
        # staticディレクトリが存在しない場合はスキップ
        return

    # /assets以下の静的ファイルを配信
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPAフォールバック: APIルート以外はすべてindex.htmlを返す
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """
        SPA用フォールバックルート

        /api, /health, /docs, /openapi.json 以外のすべてのGETリクエストで
        index.htmlを返し、フロントエンドルーターに処理を委譲する
        """
        # APIやドキュメントのパスは除外
        if full_path.startswith(("api/", "health", "docs", "openapi.json", "redoc")):
            # これらのパスは既存のルーターで処理される
            return None

        # 静的ファイル（_redirects等）をチェック
        static_file = static_dir / full_path
        if static_file.is_file():
            return FileResponse(str(static_file))

        # それ以外はすべてindex.htmlを返す（SPAルーティング）
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))

        # index.htmlが見つからない場合（通常は発生しない）
        return {"error": "SPA not found"}
