/**
 * Service Worker
 * オフライン対応とキャッシュ管理
 */

const CACHE_NAME = 'attendance-pwa-v1';
const API_CACHE_NAME = 'attendance-api-v1';
const IMAGE_CACHE_NAME = 'attendance-images-v1';

// キャッシュするファイル
const STATIC_ASSETS = [
    '/pwa/',
    '/pwa/index.html',
    '/pwa/manifest.json',
    '/pwa/css/main.css',
    '/pwa/css/animations.css',
    '/pwa/js/config.js',
    '/pwa/js/utils.js',
    '/pwa/js/enhanced-nfc-client.js',
    '/pwa/js/ui-controller.js',
    '/pwa/js/app.js'
];

// キャッシュしないパス
const NO_CACHE_PATHS = [
    '/ws/',
    '/api/v1/nfc/scan-result',
    '/api/v1/punch'
];

// オフラインページ
const OFFLINE_PAGE = '/pwa/offline.html';

/**
 * インストールイベント
 */
self.addEventListener('install', (event) => {
    console.log('[SW] Install event');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[SW] Skip waiting');
                return self.skipWaiting();
            })
    );
});

/**
 * アクティベートイベント
 */
self.addEventListener('activate', (event) => {
    console.log('[SW] Activate event');
    
    event.waitUntil(
        Promise.all([
            // 古いキャッシュを削除
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME && 
                            cacheName !== API_CACHE_NAME && 
                            cacheName !== IMAGE_CACHE_NAME) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            // すぐにコントロール開始
            self.clients.claim()
        ])
    );
});

/**
 * フェッチイベント
 */
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // WebSocketリクエストは無視
    if (url.protocol === 'ws:' || url.protocol === 'wss:') {
        return;
    }
    
    // キャッシュしないパスのチェック
    if (NO_CACHE_PATHS.some(path => url.pathname.includes(path))) {
        event.respondWith(
            fetch(request).catch(() => {
                return new Response(JSON.stringify({
                    error: 'オフラインです'
                }), {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }
    
    // 通常のリクエスト処理
    if (request.method === 'GET') {
        event.respondWith(handleGetRequest(request));
    } else if (request.method === 'POST') {
        event.respondWith(handlePostRequest(request));
    }
});

/**
 * GETリクエスト処理
 */
async function handleGetRequest(request) {
    const url = new URL(request.url);
    
    // 画像の場合
    if (isImageRequest(request)) {
        return cacheFirst(request, IMAGE_CACHE_NAME);
    }
    
    // APIリクエストの場合
    if (url.pathname.includes('/api/')) {
        return networkFirst(request, API_CACHE_NAME);
    }
    
    // 静的アセットの場合
    return cacheFirst(request, CACHE_NAME);
}

/**
 * POSTリクエスト処理
 */
async function handlePostRequest(request) {
    try {
        const response = await fetch(request);
        return response;
    } catch (error) {
        console.error('[SW] POST request failed:', error);
        
        // オフライン時はキューに追加
        if (!navigator.onLine) {
            await queueRequest(request);
            return new Response(JSON.stringify({
                queued: true,
                message: 'リクエストはオンライン復帰時に送信されます'
            }), {
                status: 202,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        throw error;
    }
}

/**
 * キャッシュファースト戦略
 */
async function cacheFirst(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
        // バックグラウンドで更新
        updateCache(request, cacheName);
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('[SW] Network request failed:', error);
        
        // オフラインページを返す
        const offlineResponse = await cache.match(OFFLINE_PAGE);
        if (offlineResponse) {
            return offlineResponse;
        }
        
        // 最後の手段
        return new Response('オフライン', {
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

/**
 * ネットワークファースト戦略
 */
async function networkFirst(request, cacheName) {
    const cache = await caches.open(cacheName);
    
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('[SW] Network request failed:', error);
        
        const cachedResponse = await cache.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        return new Response(JSON.stringify({
            error: 'ネットワークエラー',
            cached: false
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

/**
 * バックグラウンドキャッシュ更新
 */
async function updateCache(request, cacheName) {
    try {
        const cache = await caches.open(cacheName);
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            cache.put(request, networkResponse);
        }
    } catch (error) {
        console.log('[SW] Background update failed:', error);
    }
}

/**
 * 画像リクエストかチェック
 */
function isImageRequest(request) {
    const url = new URL(request.url);
    return /\.(jpg|jpeg|png|gif|webp|svg|ico)$/i.test(url.pathname);
}

/**
 * リクエストをキューに追加
 */
async function queueRequest(request) {
    const queue = await getRequestQueue();
    const serializedRequest = await serializeRequest(request);
    queue.push({
        ...serializedRequest,
        timestamp: Date.now()
    });
    await saveRequestQueue(queue);
}

/**
 * リクエストのシリアライズ
 */
async function serializeRequest(request) {
    const body = await request.text();
    return {
        url: request.url,
        method: request.method,
        headers: Object.fromEntries(request.headers.entries()),
        body: body
    };
}

/**
 * リクエストキューの取得
 */
async function getRequestQueue() {
    try {
        const cache = await caches.open('request-queue');
        const response = await cache.match('queue');
        if (response) {
            return await response.json();
        }
    } catch (error) {
        console.error('[SW] Failed to get request queue:', error);
    }
    return [];
}

/**
 * リクエストキューの保存
 */
async function saveRequestQueue(queue) {
    try {
        const cache = await caches.open('request-queue');
        const response = new Response(JSON.stringify(queue));
        await cache.put('queue', response);
    } catch (error) {
        console.error('[SW] Failed to save request queue:', error);
    }
}

/**
 * バックグラウンド同期
 */
self.addEventListener('sync', async (event) => {
    console.log('[SW] Sync event:', event.tag);
    
    if (event.tag === 'send-queued-requests') {
        event.waitUntil(sendQueuedRequests());
    }
});

/**
 * キューに入っているリクエストを送信
 */
async function sendQueuedRequests() {
    const queue = await getRequestQueue();
    const failedRequests = [];
    
    for (const requestData of queue) {
        try {
            const response = await fetch(requestData.url, {
                method: requestData.method,
                headers: requestData.headers,
                body: requestData.body
            });
            
            if (!response.ok) {
                failedRequests.push(requestData);
            }
        } catch (error) {
            console.error('[SW] Failed to send queued request:', error);
            failedRequests.push(requestData);
        }
    }
    
    // 失敗したリクエストのみ保存
    await saveRequestQueue(failedRequests);
    
    // クライアントに通知
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({
            type: 'sync-complete',
            successful: queue.length - failedRequests.length,
            failed: failedRequests.length
        });
    });
}

/**
 * プッシュ通知
 */
self.addEventListener('push', (event) => {
    console.log('[SW] Push event');
    
    const options = {
        body: event.data ? event.data.text() : '新しい通知があります',
        icon: '/pwa/icons/icon-192.png',
        badge: '/pwa/icons/badge-72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: '開く',
                icon: '/pwa/icons/checkmark.png'
            },
            {
                action: 'close',
                title: '閉じる',
                icon: '/pwa/icons/xmark.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('勤怠管理システム', options)
    );
});

/**
 * 通知クリック
 */
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification click:', event.action);
    
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/pwa/')
        );
    }
});

/**
 * メッセージ受信
 */
self.addEventListener('message', (event) => {
    console.log('[SW] Message received:', event.data);
    
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => caches.delete(cacheName))
                );
            })
        );
    }
});