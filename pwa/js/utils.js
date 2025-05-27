/**
 * ユーティリティ関数集
 * 共通で使用する汎用関数
 */

const Utils = {
    /**
     * UUID生成
     * @returns {string} UUID v4
     */
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    },

    /**
     * クライアントID生成
     * @returns {string} クライアントID
     */
    generateClientId() {
        return `pwa_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    /**
     * スキャンID生成
     * @returns {string} スキャンID
     */
    generateScanId() {
        return `scan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    /**
     * 日時フォーマット
     * @param {Date|string|number} date - 日時
     * @param {string} format - フォーマット
     * @returns {string} フォーマット済み日時
     */
    formatDateTime(date, format = 'YYYY/MM/DD HH:mm:ss') {
        const d = date instanceof Date ? date : new Date(date);
        
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');
        
        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    },

    /**
     * 相対時間表示
     * @param {Date|string|number} date - 日時
     * @returns {string} 相対時間
     */
    getRelativeTime(date) {
        const now = new Date();
        const target = date instanceof Date ? date : new Date(date);
        const diff = now - target;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'たった今';
        if (minutes < 60) return `${minutes}分前`;
        if (hours < 24) return `${hours}時間前`;
        if (days < 7) return `${days}日前`;
        
        return this.formatDateTime(target, 'MM/DD HH:mm');
    },

    /**
     * デバウンス関数
     * @param {Function} func - 実行する関数
     * @param {number} wait - 待機時間（ミリ秒）
     * @returns {Function} デバウンス関数
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * スロットル関数
     * @param {Function} func - 実行する関数
     * @param {number} limit - 制限時間（ミリ秒）
     * @returns {Function} スロットル関数
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * ローカルストレージ操作
     */
    storage: {
        /**
         * データ保存
         * @param {string} key - キー
         * @param {*} value - 値
         */
        set(key, value) {
            try {
                const data = JSON.stringify({
                    value,
                    timestamp: Date.now()
                });
                localStorage.setItem(key, data);
            } catch (e) {
                console.error('Storage set error:', e);
            }
        },

        /**
         * データ取得
         * @param {string} key - キー
         * @param {*} defaultValue - デフォルト値
         * @returns {*} 値
         */
        get(key, defaultValue = null) {
            try {
                const data = localStorage.getItem(key);
                if (!data) return defaultValue;
                
                const parsed = JSON.parse(data);
                return parsed.value;
            } catch (e) {
                console.error('Storage get error:', e);
                return defaultValue;
            }
        },

        /**
         * データ削除
         * @param {string} key - キー
         */
        remove(key) {
            try {
                localStorage.removeItem(key);
            } catch (e) {
                console.error('Storage remove error:', e);
            }
        },

        /**
         * 全データクリア
         */
        clear() {
            try {
                localStorage.clear();
            } catch (e) {
                console.error('Storage clear error:', e);
            }
        }
    },

    /**
     * エラーハンドリング
     * @param {Error} error - エラーオブジェクト
     * @returns {Object} エラー情報
     */
    parseError(error) {
        if (error.response) {
            // APIレスポンスエラー
            return {
                type: 'api',
                status: error.response.status,
                message: error.response.data?.error?.message || error.message,
                details: error.response.data
            };
        } else if (error.code === 'ECONNABORTED') {
            // タイムアウト
            return {
                type: 'timeout',
                message: '接続がタイムアウトしました',
                details: error
            };
        } else if (!navigator.onLine) {
            // オフライン
            return {
                type: 'offline',
                message: 'インターネット接続がありません',
                details: error
            };
        } else {
            // その他のエラー
            return {
                type: 'unknown',
                message: error.message || '不明なエラーが発生しました',
                details: error
            };
        }
    },

    /**
     * バイブレーション
     * @param {number|Array<number>} pattern - パターン
     */
    vibrate(pattern = 50) {
        if (Config.DEVICE.SUPPORTS_VIBRATION) {
            navigator.vibrate(pattern);
        }
    },

    /**
     * 通知表示
     * @param {string} title - タイトル
     * @param {Object} options - オプション
     */
    async showNotification(title, options = {}) {
        if (!Config.DEVICE.SUPPORTS_NOTIFICATION) return;
        
        if (Notification.permission === 'granted') {
            new Notification(title, {
                icon: '/icons/icon-192.png',
                badge: '/icons/badge-72.png',
                ...options
            });
        } else if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                new Notification(title, options);
            }
        }
    },

    /**
     * メモリ使用量チェック
     * @returns {Object|null} メモリ情報
     */
    getMemoryUsage() {
        if (performance.memory) {
            return {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit,
                percentage: (performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100
            };
        }
        return null;
    },

    /**
     * ネットワーク接続品質測定
     * @param {string} url - テストURL
     * @returns {Promise<number>} レイテンシ（ミリ秒）
     */
    async measureLatency(url = `${Config.API.BASE_URL}${Config.API.ENDPOINTS.HEALTH_CHECK}`) {
        const start = performance.now();
        try {
            await fetch(url, {
                method: 'HEAD',
                mode: 'no-cors',
                cache: 'no-cache'
            });
            const end = performance.now();
            return Math.round(end - start);
        } catch (error) {
            return Infinity;
        }
    },

    /**
     * カスタムURL生成
     * @param {string} scanId - スキャンID
     * @param {string} clientId - クライアントID
     * @returns {string} カスタムURL
     */
    generateCustomURL(scanId, clientId) {
        const params = new URLSearchParams({
            scan_id: scanId,
            client_id: clientId,
            callback: 'ws'
        });
        return `${Config.NFC.CUSTOM_URL_SCHEME}${Config.NFC.SCAN_PATH}?${params.toString()}`;
    },

    /**
     * ログ出力
     * @param {string} level - ログレベル
     * @param {string} message - メッセージ
     * @param {*} data - データ
     */
    log(level, message, data = null) {
        if (!Config.PERFORMANCE.ENABLE_LOGGING) return;
        
        const levels = ['error', 'warn', 'info', 'debug'];
        const currentLevel = levels.indexOf(Config.PERFORMANCE.LOG_LEVEL);
        const messageLevel = levels.indexOf(level);
        
        if (messageLevel <= currentLevel) {
            const timestamp = new Date().toISOString();
            const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}`;
            
            switch (level) {
                case 'error':
                    console.error(logMessage, data);
                    break;
                case 'warn':
                    console.warn(logMessage, data);
                    break;
                case 'info':
                    console.info(logMessage, data);
                    break;
                case 'debug':
                    console.log(logMessage, data);
                    break;
            }
        }
    }
};

// グローバルに公開
window.Utils = Utils;