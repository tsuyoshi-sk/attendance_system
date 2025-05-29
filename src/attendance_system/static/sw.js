/**
 * Service Worker for 勤怠管理システム PWA
 * オフライン対応・キャッシュ管理・バックグラウンド同期
 */

const CACHE_NAME = 'attendance-system-v2.0.0';
const OFFLINE_CACHE = 'attendance-offline-v1';

// キャッシュするリソース
const STATIC_RESOURCES = [
    '/',
    '/index.html',
    '/manifest.json',
    '/js/attendance-app.js',
    '/icons/icon-192x192.png',
    '/icons/icon-512x512.png'
];

// 動的にキャッシュするパターン
const CACHE_PATTERNS = [
    /^\/api\//,  // API レスポンス
    /^\/icons\//,  // アイコン
    /^\/screenshots\//  // スクリーンショット
];

// インストール時の処理
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Caching static resources');
                return cache.addAll(STATIC_RESOURCES);
            })
            .then(() => {
                console.log('Service Worker installed successfully');
                // 新しいバージョンを即座に有効化
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('Service Worker installation failed:', error);
            })
    );
});

// アクティベート時の処理
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    
    event.waitUntil(
        Promise.all([
            // 古いキャッシュを削除
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME && cacheName !== OFFLINE_CACHE) {
                            console.log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            // 新しいService Workerをすべてのタブで有効化
            self.clients.claim()
        ]).then(() => {
            console.log('Service Worker activated successfully');
        })
    );
});

// フェッチイベントの処理
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // WebSocketリクエストは処理しない
    if (url.protocol === 'ws:' || url.protocol === 'wss:') {
        return;
    }
    
    // GET リクエストのみキャッシュ対象
    if (request.method !== 'GET') {
        return;
    }
    
    event.respondWith(
        handleFetch(request)
    );
});

async function handleFetch(request) {
    const url = new URL(request.url);
    
    try {
        // キャッシュファーストストラテジー（静的リソース）
        if (isStaticResource(url.pathname)) {
            return await cacheFirst(request);
        }
        
        // ネットワークファーストストラテジー（API・動的コンテンツ）
        if (isApiRequest(url.pathname) || isDynamicContent(url.pathname)) {
            return await networkFirst(request);
        }
        
        // デフォルト：ネットワークファーストでフォールバック
        return await networkFirst(request);
        
    } catch (error) {
        console.error('Fetch handling failed:', error);
        
        // オフライン時のフォールバック
        if (url.pathname === '/' || url.pathname === '/index.html') {
            return await caches.match('/index.html');
        }
        
        return new Response(
            JSON.stringify({ 
                error: 'Network error',
                message: 'オフラインです。後でもう一度お試しください。',
                timestamp: new Date().toISOString()
            }),
            { 
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// キャッシュファーストストラテジー
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        // バックグラウンドでキャッシュを更新
        updateCacheInBackground(request);
        return cachedResponse;
    }
    
    // キャッシュにない場合はネットワークから取得
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
        const cache = await caches.open(CACHE_NAME);
        cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
}

// ネットワークファーストストラテジー
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request, {
            timeout: 5000  // 5秒タイムアウト
        });
        
        if (networkResponse.ok) {
            // 成功したレスポンスをキャッシュ
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('Network failed, trying cache:', request.url);
        
        // ネットワークエラー時はキャッシュを確認
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        throw error;
    }
}

// バックグラウンドでキャッシュを更新
async function updateCacheInBackground(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse);
        }
    } catch (error) {
        console.log('Background cache update failed:', error);
    }
}

// リソースタイプの判定
function isStaticResource(pathname) {
    const staticExtensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'];
    const staticPaths = ['/', '/index.html', '/manifest.json'];
    
    return staticPaths.includes(pathname) || 
           staticExtensions.some(ext => pathname.endsWith(ext));
}

function isApiRequest(pathname) {
    return pathname.startsWith('/api/') || 
           pathname.startsWith('/ws/') ||
           pathname.includes('/health') ||
           pathname.includes('/stats');
}

function isDynamicContent(pathname) {
    return pathname.includes('/attendance/') ||
           pathname.includes('/reports/') ||
           pathname.includes('/analytics/');
}

// バックグラウンド同期
self.addEventListener('sync', (event) => {
    console.log('Background sync triggered:', event.tag);
    
    if (event.tag === 'attendance-sync') {
        event.waitUntil(syncOfflineData());
    }
});

async function syncOfflineData() {
    try {
        // オフラインキューからデータを取得
        const clients = await self.clients.matchAll();
        
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_OFFLINE_DATA',
                timestamp: new Date().toISOString()
            });
        });
        
        console.log('Offline data sync initiated');
        
    } catch (error) {
        console.error('Offline sync failed:', error);
    }
}

// プッシュ通知
self.addEventListener('push', (event) => {
    console.log('Push notification received:', event);
    
    const options = {
        body: event.data ? event.data.text() : '勤怠管理システムからの通知',
        icon: '/icons/icon-192x192.png',
        badge: '/icons/icon-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            timestamp: new Date().toISOString(),
            url: '/'
        },
        actions: [
            {
                action: 'view',
                title: '確認する',
                icon: '/icons/view-icon.png'
            },
            {
                action: 'dismiss',
                title: '閉じる',
                icon: '/icons/close-icon.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('勤怠管理システム', options)
    );
});

// 通知クリック
self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event);
    
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/')
        );
    }
});

// メッセージ受信
self.addEventListener('message', (event) => {
    console.log('Service Worker received message:', event.data);
    
    switch (event.data.type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
            
        case 'GET_VERSION':
            event.source.postMessage({
                type: 'VERSION',
                version: CACHE_NAME
            });
            break;
            
        case 'CLEAR_CACHE':
            clearAllCaches().then(() => {
                event.source.postMessage({
                    type: 'CACHE_CLEARED'
                });
            });
            break;
    }
});

// 全キャッシュクリア
async function clearAllCaches() {
    const cacheNames = await caches.keys();
    await Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
    );
    console.log('All caches cleared');
}

// エラーハンドリング
self.addEventListener('error', (event) => {
    console.error('Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
    console.error('Service Worker unhandled promise rejection:', event.reason);
});

console.log('Service Worker script loaded successfully');