/**
 * Main Application
 * PWAのメインエントリーポイント
 */

class AttendanceApp {
    constructor() {
        this.nfcClient = null;
        this.uiController = null;
        this.serviceWorkerRegistration = null;
        this.isInitialized = false;
        
        // パフォーマンス計測開始
        this.startTime = performance.now();
        
        // DOMContentLoaded待機
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    /**
     * アプリケーション初期化
     */
    async initialize() {
        try {
            Utils.log('info', 'Initializing Attendance App');
            
            // Service Worker登録
            await this.registerServiceWorker();
            
            // 通知権限要求
            await this.requestNotificationPermission();
            
            // NFCクライアント初期化
            this.initializeNFCClient();
            
            // UIコントローラー初期化
            this.initializeUIController();
            
            // WebSocket接続開始
            await this.connectWebSocket();
            
            // パフォーマンスメトリクス
            this.reportInitializationMetrics();
            
            // 初期化完了
            this.isInitialized = true;
            
            Utils.log('info', 'Attendance App initialized successfully');
            
        } catch (error) {
            Utils.log('error', 'Failed to initialize app', error);
            this.showInitializationError(error);
        }
    }

    /**
     * Service Worker登録
     */
    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                this.serviceWorkerRegistration = await navigator.serviceWorker.register('/sw.js');
                Utils.log('info', 'Service Worker registered');
                
                // アップデート確認
                this.serviceWorkerRegistration.addEventListener('updatefound', () => {
                    Utils.log('info', 'Service Worker update found');
                    this.handleServiceWorkerUpdate();
                });
                
            } catch (error) {
                Utils.log('error', 'Service Worker registration failed', error);
            }
        }
    }

    /**
     * 通知権限要求
     */
    async requestNotificationPermission() {
        if (Config.DEVICE.SUPPORTS_NOTIFICATION && Notification.permission === 'default') {
            try {
                const permission = await Notification.requestPermission();
                Utils.log('info', 'Notification permission:', permission);
            } catch (error) {
                Utils.log('error', 'Failed to request notification permission', error);
            }
        }
    }

    /**
     * NFCクライアント初期化
     */
    initializeNFCClient() {
        this.nfcClient = new EnhancedNFCClient();
        
        // グローバルイベントハンドラー
        this.nfcClient.on('connect', () => this.handleWebSocketConnect());
        this.nfcClient.on('disconnect', () => this.handleWebSocketDisconnect());
        this.nfcClient.on('error', (error) => this.handleWebSocketError(error));
        
        // メトリクス収集
        if (Config.PERFORMANCE.ENABLE_METRICS) {
            setInterval(() => this.collectMetrics(), Config.PERFORMANCE.METRICS_INTERVAL);
        }
    }

    /**
     * UIコントローラー初期化
     */
    initializeUIController() {
        this.uiController = new UIController(this.nfcClient);
    }

    /**
     * WebSocket接続
     */
    async connectWebSocket() {
        Utils.log('info', 'Connecting to WebSocket');
        await this.nfcClient.connect();
    }

    /**
     * WebSocket接続成功ハンドラー
     */
    handleWebSocketConnect() {
        Utils.log('info', 'WebSocket connected');
        
        // 接続成功通知
        if (this.isInitialized) {
            Utils.showNotification('接続確立', {
                body: 'サーバーとの接続が確立されました',
                icon: '/icons/connected.png'
            });
        }
    }

    /**
     * WebSocket切断ハンドラー
     */
    handleWebSocketDisconnect() {
        Utils.log('warn', 'WebSocket disconnected');
    }

    /**
     * WebSocketエラーハンドラー
     */
    handleWebSocketError(error) {
        Utils.log('error', 'WebSocket error', error);
    }

    /**
     * Service Workerアップデート処理
     */
    handleServiceWorkerUpdate() {
        const newWorker = this.serviceWorkerRegistration.installing;
        
        newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // 新しいバージョンが利用可能
                this.showUpdateNotification();
            }
        });
    }

    /**
     * アップデート通知表示
     */
    showUpdateNotification() {
        const updateBanner = document.createElement('div');
        updateBanner.className = 'update-banner';
        updateBanner.innerHTML = `
            <span>新しいバージョンが利用可能です</span>
            <button onclick="location.reload()">更新</button>
        `;
        document.body.appendChild(updateBanner);
    }

    /**
     * 初期化エラー表示
     */
    showInitializationError(error) {
        const errorContainer = document.createElement('div');
        errorContainer.className = 'init-error';
        errorContainer.innerHTML = `
            <h2>初期化エラー</h2>
            <p>${error.message}</p>
            <button onclick="location.reload()">再読み込み</button>
        `;
        document.body.appendChild(errorContainer);
    }

    /**
     * メトリクス収集
     */
    collectMetrics() {
        const metrics = {
            app: {
                uptime: Date.now() - this.startTime,
                initialized: this.isInitialized
            },
            nfc: this.nfcClient.getMetrics(),
            memory: Utils.getMemoryUsage(),
            performance: {
                navigationTiming: performance.getEntriesByType('navigation')[0],
                resourceTiming: performance.getEntriesByType('resource').length
            }
        };
        
        // メモリ警告チェック
        if (metrics.memory && metrics.memory.used > Config.PERFORMANCE.MEMORY_WARNING_THRESHOLD) {
            Utils.log('warn', 'High memory usage detected', metrics.memory);
            this.performMemoryCleanup();
        }
        
        Utils.log('debug', 'Metrics collected', metrics);
    }

    /**
     * メモリクリーンアップ
     */
    performMemoryCleanup() {
        // 古いメッセージバッファをクリア
        if (this.nfcClient) {
            this.nfcClient.messageBuffer = this.nfcClient.messageBuffer.slice(-50);
        }
        
        // 不要なリソースを解放
        if ('gc' in window) {
            window.gc();
        }
    }

    /**
     * 初期化メトリクスレポート
     */
    reportInitializationMetrics() {
        const endTime = performance.now();
        const initTime = endTime - this.startTime;
        
        Utils.log('info', `App initialized in ${initTime.toFixed(2)}ms`);
        
        // パフォーマンスエントリ記録
        if (performance.mark) {
            performance.mark('app-init-complete');
            performance.measure('app-init', 'navigationStart', 'app-init-complete');
        }
    }

    /**
     * アプリケーション終了処理
     */
    destroy() {
        Utils.log('info', 'Destroying app');
        
        if (this.uiController) {
            this.uiController.destroy();
        }
        
        if (this.nfcClient) {
            this.nfcClient.disconnect();
        }
    }
}

// アプリケーション起動
const app = new AttendanceApp();

// グローバルエラーハンドリング
window.addEventListener('error', (event) => {
    Utils.log('error', 'Global error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
    });
});

window.addEventListener('unhandledrejection', (event) => {
    Utils.log('error', 'Unhandled rejection', {
        reason: event.reason,
        promise: event.promise
    });
});

// ビジビリティ変更処理
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        Utils.log('info', 'App hidden');
    } else {
        Utils.log('info', 'App visible');
        // 再接続チェック
        if (app.nfcClient && app.nfcClient.connectionState === 'disconnected') {
            app.nfcClient.connect();
        }
    }
});

// PWAインストールプロンプト
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    // インストールボタン表示
    const installButton = document.createElement('button');
    installButton.className = 'install-button';
    installButton.textContent = 'アプリをインストール';
    installButton.addEventListener('click', async () => {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        Utils.log('info', 'Install prompt outcome:', outcome);
        deferredPrompt = null;
        installButton.remove();
    });
    
    document.body.appendChild(installButton);
});

// アプリインストール完了
window.addEventListener('appinstalled', () => {
    Utils.log('info', 'PWA installed');
    Utils.showNotification('インストール完了', {
        body: '勤怠管理アプリがインストールされました',
        icon: '/icons/icon-192.png'
    });
});