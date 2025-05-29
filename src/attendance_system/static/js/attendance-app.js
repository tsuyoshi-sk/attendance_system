/**
 * 勤怠管理システム PWAクライアント
 * iPhone Suica対応 WebSocket統合版
 */

class AttendanceApp {
    constructor() {
        this.ws = null;
        this.sessionId = localStorage.getItem('sessionId') || this.generateSessionId();
        this.isOnline = navigator.onLine;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.offlineQueue = JSON.parse(localStorage.getItem('offlineQueue') || '[]');
        this.wsUrl = `ws://${window.location.hostname}:8000/ws`;
        
        this.initializeApp();
        this.setupEventListeners();
        this.connectWebSocket();
    }
    
    generateSessionId() {
        const sessionId = 'sess_' + Math.random().toString(36).substr(2, 16) + Date.now().toString(36);
        localStorage.setItem('sessionId', sessionId);
        return sessionId;
    }
    
    initializeApp() {
        this.updateTime();
        this.updateConnectionStatus(false);
        this.loadOfflineData();
        
        // 時間更新
        setInterval(() => this.updateTime(), 1000);
        
        // ハートビート送信
        setInterval(() => this.sendHeartbeat(), 30000);
        
        // オンライン/オフライン監視
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.hideOfflineIndicator();
            this.connectWebSocket();
            this.processOfflineQueue();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showOfflineIndicator();
            this.updateConnectionStatus(false);
        });
        
        console.log('勤怠管理システム PWA initialized');
    }
    
    setupEventListeners() {
        document.getElementById('scanButton').addEventListener('click', () => {
            this.startNFCScan();
        });
        
        // Service Worker登録
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(reg => console.log('Service Worker registered:', reg))
                .catch(err => console.log('Service Worker registration failed:', err));
        }
        
        // PWAインストールプロンプト
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            console.log('PWA install prompt available');
        });
    }
    
    connectWebSocket() {
        if (!this.isOnline) return;
        
        try {
            console.log('Connecting to WebSocket:', this.wsUrl);
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
                this.reconnectAttempts = 0;
                
                // 認証
                this.sendMessage({
                    type: 'session_validate',
                    payload: { 
                        session_id: this.sessionId,
                        user_agent: navigator.userAgent,
                        timestamp: new Date().toISOString()
                    }
                });
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        }
    }
    
    handleWebSocketMessage(message) {
        console.log('Received message:', message);
        
        switch (message.type) {
            case 'auth_required':
                this.showNotification('認証が必要です', 'error');
                // 簡易認証（実際はもっと堅牢な実装が必要）
                this.sendMessage({
                    type: 'session_validate',
                    payload: { 
                        session_id: this.sessionId,
                        user_id: 'demo_user_' + Date.now()
                    }
                });
                break;
                
            case 'auth_success':
                this.showNotification('認証成功！', 'success');
                localStorage.setItem('authenticated', 'true');
                break;
                
            case 'attendance_record':
                this.handleAttendanceRecord(message.payload);
                break;
                
            case 'error':
                this.showNotification(`エラー: ${message.payload.error}`, 'error');
                break;
                
            case 'heartbeat':
                // ハートビート応答受信
                console.log('Heartbeat received');
                break;
                
            case 'system_status':
                console.log('System status:', message.payload);
                break;
                
            default:
                console.log('Unknown message type:', message.type);
        }
    }
    
    async startNFCScan() {
        const scanButton = document.getElementById('scanButton');
        const nfcIcon = document.getElementById('nfcIcon');
        
        try {
            scanButton.disabled = true;
            nfcIcon.classList.add('scanning');
            this.showLoading();
            
            this.showNotification('NFCスキャンを開始します...', 'success');
            
            // Web NFC API対応チェック
            if ('NDEFReader' in window) {
                await this.performNFCScan();
            } else {
                // Web NFC未対応の場合のシミュレーション
                this.simulateNFCScan();
            }
            
        } catch (error) {
            console.error('NFC scan failed:', error);
            this.showNotification('NFCスキャンに失敗しました', 'error');
        } finally {
            setTimeout(() => {
                this.hideLoading();
                nfcIcon.classList.remove('scanning');
                scanButton.disabled = false;
            }, 3000);
        }
    }
    
    async performNFCScan() {
        try {
            const ndef = new NDEFReader();
            
            // スキャン開始
            await ndef.scan();
            this.showNotification('iPhone Suicaをかざしてください', 'success');
            
            // タイムアウト設定
            const timeoutId = setTimeout(() => {
                this.showNotification('タイムアウトしました', 'error');
            }, 10000);
            
            ndef.addEventListener('reading', ({ message, serialNumber }) => {
                clearTimeout(timeoutId);
                console.log('NFC reading detected:', serialNumber);
                this.processNFCData(serialNumber);
            });
            
        } catch (error) {
            console.error('NFC scan error:', error);
            this.showNotification('NFC機能が利用できません', 'error');
            this.simulateNFCScan();
        }
    }
    
    simulateNFCScan() {
        // デモ用のシミュレーション
        this.showNotification('デモモード: NFC読み取りをシミュレーション', 'success');
        
        setTimeout(() => {
            // ランダムなIDMを生成
            const mockIdm = Array.from({length: 16}, () => 
                Math.floor(Math.random() * 16).toString(16).toUpperCase()
            ).join('');
            
            console.log('Simulated NFC IDM:', mockIdm);
            this.processNFCData(mockIdm);
        }, 2000);
    }
    
    processNFCData(idm) {
        const nfcData = {
            type: 'nfc_scan',
            payload: {
                idm: idm,
                location: 'office',
                timestamp: new Date().toISOString(),
                device_info: {
                    user_agent: navigator.userAgent,
                    platform: navigator.platform
                }
            },
            session_id: this.sessionId,
            user_id: localStorage.getItem('user_id') || 'demo_user'
        };
        
        if (this.isOnline && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.sendMessage(nfcData);
            this.showNotification('NFC読み取り完了！処理中...', 'success');
        } else {
            // オフライン時はキューに保存
            this.offlineQueue.push(nfcData);
            localStorage.setItem('offlineQueue', JSON.stringify(this.offlineQueue));
            this.showNotification('オフライン記録を保存しました', 'error');
            
            // オフライン時の仮記録
            this.handleAttendanceRecord({
                record_id: 'offline_' + Date.now(),
                timestamp: new Date().toISOString(),
                type: Math.random() > 0.5 ? 'check_in' : 'check_out',
                location: 'office',
                status: 'offline'
            });
        }
    }
    
    handleAttendanceRecord(payload) {
        const record = {
            id: payload.record_id,
            timestamp: payload.timestamp,
            type: payload.type,
            location: payload.location,
            status: payload.status || 'online'
        };
        
        // ローカルストレージに保存
        const records = JSON.parse(localStorage.getItem('attendanceRecords') || '[]');
        
        // 重複チェック
        const existingIndex = records.findIndex(r => r.id === record.id);
        if (existingIndex >= 0) {
            records[existingIndex] = record;
        } else {
            records.unshift(record);
        }
        
        // 最新100件保持
        localStorage.setItem('attendanceRecords', JSON.stringify(records.slice(0, 100)));
        
        this.updateAttendanceHistory();
        
        const statusText = record.status === 'offline' ? ' (オフライン)' : '';
        const message = record.type === 'check_in' 
            ? `出勤を記録しました${statusText}` 
            : `退勤を記録しました${statusText}`;
        this.showNotification(message, 'success');
    }
    
    updateAttendanceHistory() {
        const records = JSON.parse(localStorage.getItem('attendanceRecords') || '[]');
        const historyContainer = document.getElementById('attendanceHistory');
        
        if (records.length === 0) {
            historyContainer.innerHTML = '<div class="history-item"><div class="history-time">本日の記録はありません</div></div>';
            return;
        }
        
        const today = new Date().toDateString();
        const todayRecords = records.filter(record => 
            new Date(record.timestamp).toDateString() === today
        );
        
        if (todayRecords.length === 0) {
            historyContainer.innerHTML = '<div class="history-item"><div class="history-time">本日の記録はありません</div></div>';
            return;
        }
        
        historyContainer.innerHTML = todayRecords.map(record => `
            <div class="history-item">
                <div>
                    <div class="history-time">${new Date(record.timestamp).toLocaleTimeString('ja-JP')}</div>
                    <div style="font-size: 0.8rem; color: #6b7280;">
                        ${record.location}${record.status === 'offline' ? ' (オフライン)' : ''}
                    </div>
                </div>
                <div class="history-type ${record.type}">
                    ${record.type === 'check_in' ? '出勤' : '退勤'}
                </div>
            </div>
        `).join('');
    }
    
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            message.timestamp = new Date().toISOString();
            this.ws.send(JSON.stringify(message));
            console.log('Sent message:', message);
        } else {
            console.warn('WebSocket not connected, message not sent:', message);
        }
    }
    
    sendHeartbeat() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.sendMessage({
                type: 'heartbeat',
                payload: { ping: 'ping' }
            });
        }
    }
    
    processOfflineQueue() {
        if (this.offlineQueue.length === 0) return;
        
        console.log(`Processing ${this.offlineQueue.length} offline messages`);
        
        this.offlineQueue.forEach(message => {
            this.sendMessage(message);
        });
        
        this.offlineQueue = [];
        localStorage.setItem('offlineQueue', JSON.stringify([]));
        
        this.showNotification(`${this.offlineQueue.length}件のオフライン記録を送信しました`, 'success');
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts && this.isOnline) {
            this.reconnectAttempts++;
            const delay = Math.min(2000 * Math.pow(2, this.reconnectAttempts - 1), 30000);
            
            console.log(`Reconnecting in ${delay}ms... Attempt ${this.reconnectAttempts}`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        } else {
            console.log('Max reconnection attempts reached or offline');
        }
    }
    
    updateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('ja-JP', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        });
        document.getElementById('currentTime').textContent = timeString;
    }
    
    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connectionStatus');
        const text = document.getElementById('connectionText');
        
        if (connected) {
            indicator.className = 'status-indicator connected';
            text.textContent = '接続済み';
        } else {
            indicator.className = 'status-indicator disconnected';
            text.textContent = '未接続';
        }
    }
    
    showNotification(message, type = 'success') {
        const notification = document.getElementById('notification');
        const messageEl = document.getElementById('notificationMessage');
        
        messageEl.textContent = message;
        notification.className = `notification ${type} show`;
        
        setTimeout(() => {
            notification.classList.remove('show');
        }, 4000);
        
        console.log(`Notification [${type}]: ${message}`);
    }
    
    showOfflineIndicator() {
        document.getElementById('offlineIndicator').style.display = 'block';
    }
    
    hideOfflineIndicator() {
        document.getElementById('offlineIndicator').style.display = 'none';
    }
    
    showLoading() {
        document.getElementById('loadingOverlay').style.display = 'flex';
    }
    
    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
    
    loadOfflineData() {
        this.updateAttendanceHistory();
    }
}

// アプリケーション初期化
document.addEventListener('DOMContentLoaded', () => {
    window.attendanceApp = new AttendanceApp();
});

// PWA インストールプロンプト
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('PWA install prompt available');
});

// デバッグ用グローバル関数
window.debugAttendance = {
    getRecords: () => JSON.parse(localStorage.getItem('attendanceRecords') || '[]'),
    clearRecords: () => localStorage.removeItem('attendanceRecords'),
    getOfflineQueue: () => JSON.parse(localStorage.getItem('offlineQueue') || '[]'),
    testNotification: (message, type) => window.attendanceApp.showNotification(message, type),
    reconnect: () => window.attendanceApp.connectWebSocket()
};