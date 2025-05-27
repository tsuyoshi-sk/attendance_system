/**
 * PWA設定ファイル
 * 環境変数と定数の管理
 */

const Config = {
    // API設定
    API: {
        BASE_URL: window.location.hostname === 'localhost' 
            ? 'http://localhost:8000' 
            : window.location.origin,
        WS_BASE_URL: window.location.hostname === 'localhost'
            ? 'ws://localhost:8000'
            : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`,
        ENDPOINTS: {
            NFC_SCAN: '/api/v1/nfc/scan-result',
            PUNCH: '/api/v1/punch',
            EMPLOYEE_STATUS: '/api/v1/employees/me',
            PUNCH_HISTORY: '/api/v1/punch/history',
            HEALTH_CHECK: '/health'
        },
        TIMEOUT: 30000, // 30秒
        RETRY_COUNT: 3,
        RETRY_DELAY: 1000 // 1秒
    },

    // WebSocket設定
    WS: {
        RECONNECT_INTERVAL: 3000, // 3秒
        MAX_RECONNECT_ATTEMPTS: 10,
        HEARTBEAT_INTERVAL: 30000, // 30秒
        PONG_TIMEOUT: 5000, // 5秒
        MESSAGE_TIMEOUT: 30000, // 30秒
        BUFFER_SIZE: 100 // メッセージバッファサイズ
    },

    // NFC設定
    NFC: {
        SCAN_TIMEOUT: 30000, // 30秒
        CUSTOM_URL_SCHEME: 'nfc-timecard://',
        SCAN_PATH: 'scan',
        DEBOUNCE_TIME: 1000 // 1秒
    },

    // UI設定
    UI: {
        ANIMATION_DURATION: 300, // ミリ秒
        SUCCESS_DISPLAY_TIME: 3000, // 3秒
        ERROR_DISPLAY_TIME: 5000, // 5秒
        NOTIFICATION_TIME: 5000, // 5秒
        UPDATE_INTERVAL: 1000 // 1秒（時刻更新）
    },

    // ローカルストレージキー
    STORAGE: {
        CLIENT_ID: 'nfc_client_id',
        EMPLOYEE_INFO: 'employee_info',
        LAST_PUNCH: 'last_punch',
        OFFLINE_QUEUE: 'offline_queue',
        SETTINGS: 'app_settings',
        SESSION_ID: 'session_id'
    },

    // セキュリティ設定
    SECURITY: {
        SESSION_TIMEOUT: 3600000, // 1時間
        CSRF_TOKEN_KEY: 'csrf_token',
        ENABLE_ENCRYPTION: false, // 開発環境では無効
        MESSAGE_SIGNING: false // 開発環境では無効
    },

    // パフォーマンス設定
    PERFORMANCE: {
        ENABLE_LOGGING: true,
        LOG_LEVEL: 'debug', // 'error', 'warn', 'info', 'debug'
        ENABLE_METRICS: true,
        METRICS_INTERVAL: 60000, // 1分
        MEMORY_WARNING_THRESHOLD: 50 * 1024 * 1024, // 50MB
        ENABLE_WORKER: typeof Worker !== 'undefined'
    },

    // 打刻種別
    PUNCH_TYPES: {
        IN: { value: 'in', label: '出勤', icon: '🏢', color: '#4caf50' },
        OUT: { value: 'out', label: '退勤', icon: '🏠', color: '#f44336' },
        OUTSIDE: { value: 'outside', label: '外出', icon: '🚶', color: '#ff9800' },
        RETURN: { value: 'return', label: '戻り', icon: '🔙', color: '#2196f3' }
    },

    // 接続品質レベル
    CONNECTION_QUALITY: {
        EXCELLENT: { min: 0, max: 50, label: '優良', class: 'excellent' },
        GOOD: { min: 51, max: 150, label: '良好', class: 'good' },
        POOR: { min: 151, max: 300, label: '不良', class: 'poor' },
        OFFLINE: { min: 301, max: Infinity, label: 'オフライン', class: 'offline' }
    },

    // デバイス設定
    DEVICE: {
        IS_IOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
        IS_ANDROID: /Android/.test(navigator.userAgent),
        IS_MOBILE: /Mobi|Android|iPhone/i.test(navigator.userAgent),
        SUPPORTS_VIBRATION: 'vibrate' in navigator,
        SUPPORTS_NOTIFICATION: 'Notification' in window
    }
};

// 環境に応じた設定の上書き
if (window.location.hostname !== 'localhost') {
    Config.SECURITY.ENABLE_ENCRYPTION = true;
    Config.SECURITY.MESSAGE_SIGNING = true;
    Config.PERFORMANCE.LOG_LEVEL = 'error';
}

// 設定の凍結（変更不可にする）
Object.freeze(Config);
Object.keys(Config).forEach(key => {
    if (typeof Config[key] === 'object') {
        Object.freeze(Config[key]);
    }
});

// グローバルに公開
window.Config = Config;