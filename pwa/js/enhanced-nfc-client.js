/**
 * Enhanced NFC Client
 * WebSocket通信と自動再接続、ハートビート機能を持つNFCクライアント
 */

class EnhancedNFCClient {
    constructor() {
        // WebSocket関連
        this.ws = null;
        this.clientId = Utils.storage.get(Config.STORAGE.CLIENT_ID) || Utils.generateClientId();
        this.sessionId = Utils.generateUUID();
        this.wsUrl = `${Config.WS.WS_BASE_URL}/ws/nfc/${this.clientId}`;
        
        // 接続管理
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = Config.WS.MAX_RECONNECT_ATTEMPTS;
        this.reconnectTimer = null;
        this.isReconnecting = false;
        this.connectionState = 'disconnected'; // disconnected, connecting, connected
        
        // ハートビート
        this.heartbeatInterval = null;
        this.pongTimeout = null;
        this.lastPongTime = Date.now();
        
        // 接続品質
        this.connectionQuality = 'unknown';
        this.latencyHistory = [];
        this.maxLatencyHistory = 10;
        
        // メッセージ管理
        this.messageQueue = [];
        this.pendingRequests = new Map();
        this.messageBuffer = [];
        this.maxBufferSize = Config.WS.BUFFER_SIZE;
        
        // NFCスキャン状態
        this.isScanning = false;
        this.currentScanId = null;
        this.scanTimeout = null;
        this.activeRequests = new Set();
        
        // イベントハンドラー
        this.eventHandlers = {
            connect: [],
            disconnect: [],
            message: [],
            error: [],
            stateChange: [],
            qualityChange: []
        };
        
        // メトリクス
        this.metrics = {
            messagesReceived: 0,
            messagesSent: 0,
            reconnectCount: 0,
            errors: 0,
            startTime: Date.now()
        };
        
        // 初期化
        this.initialize();
    }

    /**
     * 初期化処理
     */
    initialize() {
        // クライアントIDを保存
        Utils.storage.set(Config.STORAGE.CLIENT_ID, this.clientId);
        
        // イベントリスナーをバインドして保存（後でクリーンアップ用）
        this.handleOnlineBound = () => this.handleOnline();
        this.handleOfflineBound = () => this.handleOffline();
        this.handleBeforeUnloadBound = () => this.cleanup();
        
        // オンライン/オフラインイベント
        window.addEventListener('online', this.handleOnlineBound);
        window.addEventListener('offline', this.handleOfflineBound);
        
        // ページ離脱時の処理
        window.addEventListener('beforeunload', this.handleBeforeUnloadBound);
        
        // 定期的な品質チェック
        if (!this.qualityCheckInterval) {
            this.qualityCheckInterval = setInterval(() => this.checkConnectionQuality(), 30000);
        }
        
        Utils.log('info', 'EnhancedNFCClient initialized', {
            clientId: this.clientId,
            sessionId: this.sessionId
        });
    }

    /**
     * WebSocket接続
     */
    async connect() {
        if (this.connectionState === 'connected' || this.connectionState === 'connecting') {
            Utils.log('debug', 'Already connected or connecting');
            return;
        }

        this.updateConnectionState('connecting');
        
        try {
            // 既存の接続をクリーンアップ
            this.cleanup();
            
            // WebSocket作成
            this.ws = new WebSocket(this.wsUrl);
            
            // イベントハンドラー設定
            this.setupWebSocketHandlers();
            
            // 接続タイムアウト
            const connectTimeout = setTimeout(() => {
                if (this.connectionState === 'connecting') {
                    this.ws.close();
                    this.handleError(new Error('接続タイムアウト'));
                }
            }, Config.API.TIMEOUT);
            
            // 接続成功を待つ
            await new Promise((resolve, reject) => {
                this.ws.addEventListener('open', () => {
                    clearTimeout(connectTimeout);
                    resolve();
                }, { once: true });
                
                this.ws.addEventListener('error', (error) => {
                    clearTimeout(connectTimeout);
                    reject(error);
                }, { once: true });
            });
            
        } catch (error) {
            this.handleError(error);
            this.scheduleReconnect();
        }
    }

    /**
     * WebSocketイベントハンドラー設定
     */
    setupWebSocketHandlers() {
        this.ws.addEventListener('open', this.handleOpen.bind(this));
        this.ws.addEventListener('message', this.handleMessage.bind(this));
        this.ws.addEventListener('error', this.handleError.bind(this));
        this.ws.addEventListener('close', this.handleClose.bind(this));
    }

    /**
     * 接続成功ハンドラー
     */
    handleOpen() {
        Utils.log('info', 'WebSocket connected');
        
        this.updateConnectionState('connected');
        this.reconnectAttempts = 0;
        this.isReconnecting = false;
        
        // ハートビート開始
        this.startHeartbeat();
        
        // キューに入っているメッセージを送信
        this.flushMessageQueue();
        
        // 接続イベント発火
        this.emit('connect', { clientId: this.clientId });
        
        // 接続品質チェック
        this.checkConnectionQuality();
        
        // 初期メッセージ送信
        this.send({
            type: 'client_info',
            clientId: this.clientId,
            sessionId: this.sessionId,
            userAgent: navigator.userAgent,
            timestamp: Date.now()
        });
    }

    /**
     * メッセージ受信ハンドラー
     */
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            
            this.metrics.messagesReceived++;
            this.lastPongTime = Date.now();
            
            Utils.log('debug', 'Message received', message);
            
            // メッセージタイプ別処理
            switch (message.type) {
                case 'pong':
                    this.handlePong(message);
                    break;
                    
                case 'nfc_scan_result':
                    this.handleNFCScanResult(message);
                    break;
                    
                case 'error':
                    this.handleServerError(message);
                    break;
                    
                case 'connection_info':
                    this.handleConnectionInfo(message);
                    break;
                    
                default:
                    // カスタムメッセージハンドラー
                    this.emit('message', message);
            }
            
            // メッセージバッファに追加
            this.addToBuffer(message);
            
        } catch (error) {
            Utils.log('error', 'Failed to parse message', error);
            this.metrics.errors++;
        }
    }

    /**
     * エラーハンドラー
     */
    handleError(error) {
        Utils.log('error', 'WebSocket error', error);
        
        this.metrics.errors++;
        this.emit('error', error);
        
        // エラー通知
        if (navigator.onLine) {
            Utils.showNotification('接続エラー', {
                body: 'WebSocket接続でエラーが発生しました',
                icon: '/icons/error.png'
            });
        }
    }

    /**
     * 接続終了ハンドラー
     */
    handleClose(event) {
        Utils.log('info', 'WebSocket closed', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
        });
        
        this.updateConnectionState('disconnected');
        this.stopHeartbeat();
        
        // 切断イベント発火
        this.emit('disconnect', {
            code: event.code,
            reason: event.reason
        });
        
        // 意図的な切断でない場合は再接続
        if (!event.wasClean && navigator.onLine) {
            this.scheduleReconnect();
        }
    }

    /**
     * Pongメッセージ処理
     */
    handlePong(message) {
        if (this.pongTimeout) {
            clearTimeout(this.pongTimeout);
            this.pongTimeout = null;
        }
        
        // レイテンシ計算
        const latency = Date.now() - (message.timestamp || this.lastPingTime);
        this.latencyHistory.push(latency);
        
        if (this.latencyHistory.length > this.maxLatencyHistory) {
            this.latencyHistory.shift();
        }
        
        // 接続品質更新
        this.updateConnectionQuality();
    }

    /**
     * NFCスキャン結果処理
     */
    handleNFCScanResult(message) {
        const { scan_id, success, card_id, error_message } = message.data;
        
        // スキャンタイムアウトクリア
        if (this.scanTimeout) {
            clearTimeout(this.scanTimeout);
            this.scanTimeout = null;
        }
        
        // ペンディングリクエスト処理
        const pendingRequest = this.pendingRequests.get(scan_id);
        if (pendingRequest) {
            if (success) {
                pendingRequest.resolve({ card_id, scan_id });
            } else {
                pendingRequest.reject(new Error(error_message || 'スキャン失敗'));
            }
            this.pendingRequests.delete(scan_id);
            this.activeRequests.delete(scan_id);
        }
        
        // スキャン状態更新
        this.isScanning = false;
        this.currentScanId = null;
        
        // イベント発火
        this.emit('nfc_scan_complete', {
            scan_id,
            success,
            card_id,
            error_message
        });
    }

    /**
     * サーバーエラー処理
     */
    handleServerError(message) {
        Utils.log('error', 'Server error', message);
        
        const error = new Error(message.error || 'サーバーエラー');
        error.code = message.code;
        error.details = message.details;
        
        this.emit('error', error);
    }

    /**
     * 接続情報処理
     */
    handleConnectionInfo(message) {
        const { connected_clients, server_time } = message.data;
        
        Utils.log('info', 'Connection info', {
            connectedClients: connected_clients,
            serverTime: server_time
        });
    }

    /**
     * メッセージ送信
     */
    send(data) {
        const message = {
            ...data,
            clientId: this.clientId,
            timestamp: Date.now()
        };
        
        if (this.connectionState === 'connected' && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(message));
                this.metrics.messagesSent++;
                Utils.log('debug', 'Message sent', message);
            } catch (error) {
                Utils.log('error', 'Failed to send message', error);
                this.queueMessage(message);
            }
        } else {
            // オフライン時はキューに追加
            this.queueMessage(message);
            Utils.log('debug', 'Message queued', message);
        }
    }
    
    /**
     * メッセージをキューに追加（バックプレッシャー対応）
     */
    queueMessage(message) {
        const maxQueueSize = Config.WS.MAX_QUEUE_SIZE || 100;
        
        if (this.messageQueue.length >= maxQueueSize) {
            // 最も古いメッセージを削除
            const removed = this.messageQueue.shift();
            Utils.log('warn', 'Message queue full, dropping oldest message', removed);
        }
        
        this.messageQueue.push(message);
    }

    /**
     * NFCスキャン要求
     */
    async requestNFCScan() {
        if (this.isScanning) {
            throw new Error('既にスキャン中です');
        }
        
        const scanId = Utils.generateScanId();
        
        // 重複リクエストのチェック
        if (this.activeRequests.has(scanId)) {
            Utils.log('warn', 'Duplicate scan request detected', { scanId });
            return;
        }
        
        this.activeRequests.add(scanId);
        this.currentScanId = scanId;
        this.isScanning = true;
        
        return new Promise((resolve, reject) => {
            // タイムアウト設定
            this.scanTimeout = setTimeout(() => {
                this.isScanning = false;
                this.currentScanId = null;
                this.pendingRequests.delete(scanId);
                this.activeRequests.delete(scanId);
                reject(new Error('スキャンタイムアウト'));
            }, Config.NFC.SCAN_TIMEOUT);
            
            // ペンディングリクエスト登録
            this.pendingRequests.set(scanId, { resolve, reject });
            
            // カスタムURL生成
            const customUrl = Utils.generateCustomURL(scanId, this.clientId);
            
            // NFCアプリ起動
            window.location.href = customUrl;
            
            Utils.log('info', 'NFC scan requested', {
                scanId,
                customUrl
            });
        });
    }

    /**
     * ハートビート開始
     */
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.heartbeatInterval = setInterval(() => {
            if (this.connectionState === 'connected') {
                this.lastPingTime = Date.now();
                this.send({ type: 'ping' });
                
                // Pongタイムアウト
                this.pongTimeout = setTimeout(() => {
                    Utils.log('warn', 'Pong timeout');
                    this.ws.close();
                }, Config.WS.PONG_TIMEOUT);
            }
        }, Config.WS.HEARTBEAT_INTERVAL);
    }

    /**
     * ハートビート停止
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        
        if (this.pongTimeout) {
            clearTimeout(this.pongTimeout);
            this.pongTimeout = null;
        }
    }

    /**
     * 再接続スケジュール
     */
    scheduleReconnect() {
        if (this.isReconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
            return;
        }
        
        this.isReconnecting = true;
        this.reconnectAttempts++;
        
        const delay = Math.min(
            Config.WS.RECONNECT_INTERVAL * Math.pow(2, this.reconnectAttempts - 1),
            30000
        );
        
        Utils.log('info', `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, delay);
        
        this.metrics.reconnectCount++;
    }

    /**
     * メッセージキューフラッシュ
     */
    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }

    /**
     * 接続品質チェック
     */
    async checkConnectionQuality() {
        if (this.connectionState !== 'connected') {
            this.updateConnectionQuality('offline');
            return;
        }
        
        const latency = await Utils.measureLatency();
        this.latencyHistory.push(latency);
        
        if (this.latencyHistory.length > this.maxLatencyHistory) {
            this.latencyHistory.shift();
        }
        
        this.updateConnectionQuality();
    }

    /**
     * 接続品質更新
     */
    updateConnectionQuality(quality = null) {
        if (quality) {
            this.connectionQuality = quality;
        } else {
            // 平均レイテンシ計算
            const avgLatency = this.latencyHistory.length > 0
                ? this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length
                : Infinity;
            
            // 品質判定
            for (const [key, value] of Object.entries(Config.CONNECTION_QUALITY)) {
                if (avgLatency >= value.min && avgLatency <= value.max) {
                    this.connectionQuality = key.toLowerCase();
                    break;
                }
            }
        }
        
        this.emit('qualityChange', {
            quality: this.connectionQuality,
            latency: this.latencyHistory[this.latencyHistory.length - 1] || null
        });
    }

    /**
     * 接続状態更新
     */
    updateConnectionState(state) {
        const previousState = this.connectionState;
        this.connectionState = state;
        
        if (previousState !== state) {
            this.emit('stateChange', {
                previous: previousState,
                current: state
            });
        }
    }

    /**
     * メッセージバッファ追加
     */
    addToBuffer(message) {
        this.messageBuffer.push({
            ...message,
            receivedAt: Date.now()
        });
        
        if (this.messageBuffer.length > this.maxBufferSize) {
            this.messageBuffer.shift();
        }
    }

    /**
     * オンライン復帰処理
     */
    handleOnline() {
        Utils.log('info', 'Network online');
        if (this.connectionState === 'disconnected') {
            this.connect();
        }
    }

    /**
     * オフライン処理
     */
    handleOffline() {
        Utils.log('info', 'Network offline');
        this.updateConnectionQuality('offline');
    }

    /**
     * イベント登録
     */
    on(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].push(handler);
        }
    }

    /**
     * イベント解除
     */
    off(event, handler) {
        if (this.eventHandlers[event]) {
            const index = this.eventHandlers[event].indexOf(handler);
            if (index > -1) {
                this.eventHandlers[event].splice(index, 1);
            }
        }
    }

    /**
     * イベント発火
     */
    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    Utils.log('error', `Event handler error for ${event}`, error);
                }
            });
        }
    }

    /**
     * 切断
     */
    disconnect() {
        this.cleanup();
        this.updateConnectionState('disconnected');
    }

    /**
     * クリーンアップ
     */
    cleanup() {
        this.stopHeartbeat();
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        if (this.scanTimeout) {
            clearTimeout(this.scanTimeout);
            this.scanTimeout = null;
        }
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        
        this.messageQueue = [];
        this.pendingRequests.clear();
    }

    /**
     * クリーンアップ処理
     */
    cleanup() {
        Utils.log('info', 'Cleaning up EnhancedNFCClient');
        
        // イベントリスナーの削除
        if (this.handleOnlineBound) {
            window.removeEventListener('online', this.handleOnlineBound);
        }
        if (this.handleOfflineBound) {
            window.removeEventListener('offline', this.handleOfflineBound);
        }
        if (this.handleBeforeUnloadBound) {
            window.removeEventListener('beforeunload', this.handleBeforeUnloadBound);
        }
        
        // インターバルのクリア
        if (this.qualityCheckInterval) {
            clearInterval(this.qualityCheckInterval);
            this.qualityCheckInterval = null;
        }
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        
        // タイムアウトのクリア
        if (this.pongTimeout) {
            clearTimeout(this.pongTimeout);
            this.pongTimeout = null;
        }
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.scanTimeout) {
            clearTimeout(this.scanTimeout);
            this.scanTimeout = null;
        }
        
        // WebSocket接続のクローズ
        this.disconnect();
        
        // メモリの解放
        this.messageQueue = [];
        this.pendingRequests.clear();
        this.messageBuffer = [];
        this.latencyHistory = [];
        this.eventHandlers = {
            connect: [],
            disconnect: [],
            message: [],
            error: [],
            stateChange: [],
            qualityChange: []
        };
    }

    /**
     * メトリクス取得
     */
    getMetrics() {
        const uptime = Date.now() - this.metrics.startTime;
        const avgLatency = this.latencyHistory.length > 0
            ? this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length
            : null;
        
        return {
            ...this.metrics,
            uptime,
            avgLatency,
            connectionQuality: this.connectionQuality,
            connectionState: this.connectionState,
            queuedMessages: this.messageQueue.length,
            bufferSize: this.messageBuffer.length
        };
    }
}

// グローバルに公開
window.EnhancedNFCClient = EnhancedNFCClient;