"""
PWAテスト用共通フィクスチャ

Playwrightを使用したブラウザ自動化テストの共通設定
"""

import pytest
from playwright.sync_api import Page, BrowserContext, Browser, sync_playwright
import os
from typing import Generator

# ベースURL（環境変数で上書き可能）
BASE_URL = os.getenv("PWA_BASE_URL", "http://localhost:8000")
PWA_URL = f"{BASE_URL}/pwa/"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    ブラウザコンテキストの共通設定
    """
    return {
        **browser_context_args,
        "viewport": {"width": 390, "height": 844},  # iPhone 13/14/15
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "has_touch": True,
        "is_mobile": True,
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
        "permissions": ["notifications"],  # 通知権限
        "service_workers": "allow",  # Service Worker有効化
    }


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """
    各テスト用の独立したブラウザコンテキスト
    """
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        has_touch=True,
        is_mobile=True,
        locale="ja-JP",
        timezone_id="Asia/Tokyo",
        permissions=["notifications"],
        service_workers="allow",
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """
    各テスト用の新しいページ
    """
    page = context.new_page()

    # コンソールログのキャプチャ
    page.on("console", lambda msg: print(f"[Browser {msg.type}] {msg.text}"))

    # ページエラーのキャプチャ
    page.on("pageerror", lambda exc: print(f"[Page Error] {exc}"))

    yield page
    page.close()


@pytest.fixture(scope="function")
def pwa_page(page: Page) -> Page:
    """
    PWAページを開いた状態のページオブジェクト
    """
    page.goto(PWA_URL, wait_until="networkidle")
    return page


@pytest.fixture(scope="session")
def desktop_viewport():
    """
    デスクトップ用のビューポート設定
    """
    return {"width": 1920, "height": 1080}


@pytest.fixture(scope="session")
def tablet_viewport():
    """
    タブレット用のビューポート設定
    """
    return {"width": 768, "height": 1024}


@pytest.fixture(scope="session")
def mobile_viewport():
    """
    モバイル用のビューポート設定（デフォルト）
    """
    return {"width": 390, "height": 844}


@pytest.fixture(scope="function")
def offline_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """
    オフライン環境をシミュレートするコンテキスト
    """
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        has_touch=True,
        is_mobile=True,
        locale="ja-JP",
        timezone_id="Asia/Tokyo",
        service_workers="allow",
    )

    # オフライン設定
    context.set_offline(True)

    yield context
    context.close()


@pytest.fixture(scope="function")
def screenshot_on_failure(request, page: Page):
    """
    テスト失敗時に自動スクリーンショット保存
    """
    yield

    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        screenshot_dir = "test-results/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)

        screenshot_path = f"{screenshot_dir}/{request.node.name}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved: {screenshot_path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    テスト結果をフィクスチャで使用できるようにする
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="function")
def wait_for_service_worker(page: Page):
    """
    Service Workerが登録されるまで待機
    """
    def wait():
        page.wait_for_function(
            """
            () => {
                return navigator.serviceWorker.ready.then(reg => {
                    return reg.active !== null;
                });
            }
            """,
            timeout=10000
        )
    return wait


@pytest.fixture(scope="function")
def clear_service_worker(page: Page):
    """
    Service Workerをクリア
    """
    def clear():
        page.evaluate(
            """
            async () => {
                const registrations = await navigator.serviceWorker.getRegistrations();
                for (let registration of registrations) {
                    await registration.unregister();
                }
            }
            """
        )
    return clear


@pytest.fixture(scope="function")
def clear_cache(page: Page):
    """
    キャッシュをクリア
    """
    def clear():
        page.evaluate(
            """
            async () => {
                const cacheNames = await caches.keys();
                for (let cacheName of cacheNames) {
                    await caches.delete(cacheName);
                }
            }
            """
        )
    return clear


# マーカー定義
def pytest_configure(config):
    """
    カスタムマーカーの登録
    """
    config.addinivalue_line(
        "markers", "service_worker: Service Worker関連のテスト"
    )
    config.addinivalue_line(
        "markers", "offline: オフライン動作のテスト"
    )
    config.addinivalue_line(
        "markers", "spa: SPAルーティングのテスト"
    )
    config.addinivalue_line(
        "markers", "ui: UI/UXのテスト"
    )
    config.addinivalue_line(
        "markers", "accessibility: アクセシビリティのテスト"
    )
    config.addinivalue_line(
        "markers", "slow: 実行時間が長いテスト"
    )
