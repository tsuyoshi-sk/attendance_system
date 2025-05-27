/**
 * UI Controller
 * ユーザーインターフェースの制御とリアルタイム更新
 */

class UIController {
    constructor(nfcClient) {
        this.nfcClient = nfcClient;
        this.elements = {};
        this.timers = {};
        this.state = {
            isScanning: false,
            lastPunch: null,
            employeeInfo: null,
            connectionStatus: 'disconnected',
            connectionQuality: 'unknown'
        };
        
        this.initialize();
    }

    /**
     * 初期化
     */
    initialize() {
        // DOM要素の取得
        this.cacheElements();
        
        // イベントリスナー設定
        this.attachEventListeners();
        
        // NFCクライアントイベント登録
        this.registerNFCEvents();
        
        // 初期状態設定
        this.loadInitialState();
        
        // 時刻更新開始
        this.startTimeUpdate();
        
        Utils.log('info', 'UIController initialized');
    }

    /**
     * DOM要素キャッシュ
     */
    cacheElements() {
        // 接続状態
        this.elements.connectionStatus = document.getElementById('connectionStatus');
        this.elements.statusIcon = document.querySelector('.status-icon');
        this.elements.statusText = document.querySelector('.status-text');
        
        // ステータスカード
        this.elements.statusCard = document.getElementById('statusCard');
        this.elements.employeeInfo = document.getElementById('employeeInfo');
        this.elements.employeeName = document.querySelector('.employee-name');
        this.elements.employeeCode = document.querySelector('.employee-code');
        this.elements.currentTime = document.getElementById('currentTime');
        this.elements.timeDisplay = document.querySelector('.time-display');
        this.elements.dateDisplay = document.querySelector('.date-display');
        
        // スキャンセクション
        this.elements.scanContainer = document.getElementById('scanContainer');
        this.elements.scanReady = document.getElementById('scanReady');
        this.elements.scanProgress = document.getElementById('scanProgress');
        this.elements.scanSuccess = document.getElementById('scanSuccess');
        this.elements.scanError = document.getElementById('scanError');
        this.elements.scanButton = document.getElementById('scanButton');
        this.elements.retryButton = document.getElementById('retryButton');
        
        // 履歴セクション
        this.elements.historyList = document.getElementById('historyList');
        
        // 接続品質
        this.elements.connectionQuality = document.getElementById('connectionQuality');
        this.elements.qualityIndicator = document.querySelector('.quality-indicator');
        this.elements.qualityText = document.querySelector('.quality-text');
        
        // その他
        this.elements.offlineBanner = document.getElementById('offlineBanner');
        this.elements.loadingOverlay = document.getElementById('loadingOverlay');
    }

    /**
     * イベントリスナー設定
     */
    attachEventListeners() {
        // スキャンボタン
        this.elements.scanButton.addEventListener('click', () => this.handleScanClick());
        
        // リトライボタン
        this.elements.retryButton.addEventListener('click', () => this.handleRetryClick());
        
        // キーボードショートカット
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !this.state.isScanning) {
                this.handleScanClick();
            }
        });
        
        // オンライン/オフライン
        window.addEventListener('online', () => this.updateOnlineStatus(true));
        window.addEventListener('offline', () => this.updateOnlineStatus(false));
    }

    /**
     * NFCクライアントイベント登録
     */
    registerNFCEvents() {
        // 接続状態変更
        this.nfcClient.on('stateChange', (data) => {
            this.updateConnectionStatus(data.current);
        });
        
        // 接続品質変更
        this.nfcClient.on('qualityChange', (data) => {
            this.updateConnectionQuality(data.quality, data.latency);
        });
        
        // NFCスキャン完了
        this.nfcClient.on('nfc_scan_complete', (data) => {
            this.handleScanComplete(data);
        });
        
        // エラー
        this.nfcClient.on('error', (error) => {
            this.showError(error.message || 'エラーが発生しました');
        });
        
        // メッセージ受信
        this.nfcClient.on('message', (message) => {
            if (message.type === 'employee_info') {
                this.updateEmployeeInfo(message.data);
            }
        });
    }

    /**
     * 初期状態読み込み
     */
    loadInitialState() {
        // 従業員情報
        const employeeInfo = Utils.storage.get(Config.STORAGE.EMPLOYEE_INFO);
        if (employeeInfo) {
            this.updateEmployeeInfo(employeeInfo);
        }
        
        // 最後の打刻
        const lastPunch = Utils.storage.get(Config.STORAGE.LAST_PUNCH);
        if (lastPunch) {
            this.state.lastPunch = lastPunch;
        }
        
        // 履歴読み込み
        this.loadPunchHistory();
    }

    /**
     * スキャンボタンクリック
     */
    async handleScanClick() {
        if (this.state.isScanning) return;
        
        // 振動フィードバック
        Utils.vibrate();
        
        try {
            this.showScanProgress();
            
            // NFCスキャン要求
            const result = await this.nfcClient.requestNFCScan();
            
            // 成功処理は nfc_scan_complete イベントで行う
            
        } catch (error) {
            Utils.log('error', 'Scan failed', error);
            this.showError(error.message);
        }
    }

    /**
     * リトライボタンクリック
     */
    handleRetryClick() {
        this.showScanReady();
        this.handleScanClick();
    }

    /**
     * スキャン完了処理
     */
    async handleScanComplete(data) {
        const { scan_id, success, card_id, error_message } = data;
        
        if (success) {
            try {
                // 打刻API呼び出し
                const response = await this.callPunchAPI(card_id);
                
                // 成功表示
                this.showScanSuccess(response);
                
                // 履歴更新
                this.addPunchToHistory(response.punch);
                
                // 最後の打刻を保存
                this.state.lastPunch = response.punch;
                Utils.storage.set(Config.STORAGE.LAST_PUNCH, response.punch);
                
                // 成功通知
                Utils.showNotification('打刻完了', {
                    body: `${response.punch.punch_type_display}を記録しました`,
                    icon: '/icons/success.png'
                });
                
            } catch (error) {
                this.showError(error.message);
            }
        } else {
            this.showError(error_message || 'スキャンに失敗しました');
        }
    }

    /**
     * 打刻API呼び出し
     */
    async callPunchAPI(cardId) {
        this.showLoading(true);
        
        try {
            const response = await fetch(`${Config.API.BASE_URL}${Config.API.ENDPOINTS.PUNCH}?card_idm=${cardId}&punch_type=in`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error?.message || 'APIエラー');
            }
            
            return await response.json();
            
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * スキャン待機状態表示
     */
    showScanReady() {
        this.state.isScanning = false;
        this.hideAllScanStates();
        this.elements.scanReady.style.display = 'block';
        this.elements.scanButton.disabled = false;
    }

    /**
     * スキャン中表示
     */
    showScanProgress() {
        this.state.isScanning = true;
        this.hideAllScanStates();
        this.elements.scanProgress.style.display = 'block';
        this.elements.scanButton.disabled = true;
        
        // プログレスバーアニメーション開始
        const progressFill = this.elements.scanProgress.querySelector('.progress-fill');
        progressFill.style.animation = 'none';
        setTimeout(() => {
            progressFill.style.animation = '';
        }, 10);
    }

    /**
     * スキャン成功表示
     */
    showScanSuccess(response) {
        this.state.isScanning = false;
        this.hideAllScanStates();
        this.elements.scanSuccess.style.display = 'block';
        
        // 成功メッセージ更新
        const successMessage = this.elements.scanSuccess.querySelector('.success-message');
        successMessage.textContent = `${response.employee.name}さんの${response.message}`;
        
        // 打刻詳細更新
        const punchType = this.elements.scanSuccess.querySelector('.punch-type');
        const punchTime = this.elements.scanSuccess.querySelector('.punch-time');
        
        punchType.textContent = response.punch.punch_type_display;
        punchTime.textContent = Utils.formatDateTime(response.punch.punch_time, 'HH:mm:ss');
        
        // 振動フィードバック
        Utils.vibrate([50, 50, 50]);
        
        // 自動的に待機状態に戻る
        this.timers.successReset = setTimeout(() => {
            this.showScanReady();
        }, Config.UI.SUCCESS_DISPLAY_TIME);
    }

    /**
     * エラー表示
     */
    showError(message) {
        this.state.isScanning = false;
        this.hideAllScanStates();
        this.elements.scanError.style.display = 'block';
        
        const errorMessage = this.elements.scanError.querySelector('.error-message');
        errorMessage.textContent = message;
        
        // エラー振動
        Utils.vibrate([100, 50, 100]);
    }

    /**
     * 全スキャン状態非表示
     */
    hideAllScanStates() {
        this.elements.scanReady.style.display = 'none';
        this.elements.scanProgress.style.display = 'none';
        this.elements.scanSuccess.style.display = 'none';
        this.elements.scanError.style.display = 'none';
        
        // タイマークリア
        if (this.timers.successReset) {
            clearTimeout(this.timers.successReset);
        }
    }

    /**
     * 接続状態更新
     */
    updateConnectionStatus(status) {
        this.state.connectionStatus = status;
        
        // アイコン更新
        this.elements.statusIcon.className = 'status-icon';
        if (status === 'connected') {
            this.elements.statusIcon.classList.add('connected');
        } else if (status === 'disconnected') {
            this.elements.statusIcon.classList.add('disconnected');
        }
        
        // テキスト更新
        const statusTexts = {
            connected: '接続済み',
            connecting: '接続中...',
            disconnected: '未接続'
        };
        this.elements.statusText.textContent = statusTexts[status] || status;
    }

    /**
     * 接続品質更新
     */
    updateConnectionQuality(quality, latency) {
        this.state.connectionQuality = quality;
        
        // インジケーター更新
        this.elements.qualityIndicator.className = 'quality-indicator';
        if (quality !== 'unknown' && quality !== 'offline') {
            this.elements.qualityIndicator.classList.add(quality);
        }
        
        // テキスト更新
        const qualityConfig = Config.CONNECTION_QUALITY[quality.toUpperCase()];
        if (qualityConfig) {
            const latencyText = latency ? ` (${latency}ms)` : '';
            this.elements.qualityText.textContent = `接続品質: ${qualityConfig.label}${latencyText}`;
        }
    }

    /**
     * 従業員情報更新
     */
    updateEmployeeInfo(info) {
        this.state.employeeInfo = info;
        
        if (info) {
            this.elements.employeeName.textContent = info.name;
            this.elements.employeeCode.textContent = `社員番号: ${info.employee_code}`;
            this.elements.employeeInfo.style.display = 'block';
            
            // ローカルストレージに保存
            Utils.storage.set(Config.STORAGE.EMPLOYEE_INFO, info);
        } else {
            this.elements.employeeInfo.style.display = 'none';
        }
    }

    /**
     * 時刻更新開始
     */
    startTimeUpdate() {
        const updateTime = () => {
            const now = new Date();
            this.elements.timeDisplay.textContent = Utils.formatDateTime(now, 'HH:mm:ss');
            this.elements.dateDisplay.textContent = Utils.formatDateTime(now, 'YYYY年MM月DD日');
        };
        
        updateTime();
        this.timers.timeUpdate = setInterval(updateTime, Config.UI.UPDATE_INTERVAL);
    }

    /**
     * 打刻履歴読み込み
     */
    async loadPunchHistory() {
        try {
            const response = await fetch(
                `${Config.API.BASE_URL}${Config.API.ENDPOINTS.PUNCH_HISTORY}/1?date=${Utils.formatDateTime(new Date(), 'YYYY-MM-DD')}`
            );
            
            if (response.ok) {
                const data = await response.json();
                this.displayPunchHistory(data.punch_records || []);
            }
        } catch (error) {
            Utils.log('error', 'Failed to load punch history', error);
        }
    }

    /**
     * 打刻履歴表示
     */
    displayPunchHistory(records) {
        if (records.length === 0) {
            this.elements.historyList.innerHTML = '<p class="empty-message">本日の打刻はありません</p>';
            return;
        }
        
        const html = records.map(record => {
            const punchType = Config.PUNCH_TYPES[record.punch_type.toUpperCase()];
            return `
                <div class="history-item">
                    <div class="history-time">
                        ${Utils.formatDateTime(record.punch_time, 'HH:mm')}
                    </div>
                    <div class="history-type">
                        <span class="punch-type-badge ${record.punch_type}">
                            ${punchType ? punchType.label : record.punch_type}
                        </span>
                    </div>
                </div>
            `;
        }).join('');
        
        this.elements.historyList.innerHTML = html;
    }

    /**
     * 履歴に打刻追加
     */
    addPunchToHistory(punch) {
        // 空メッセージを削除
        const emptyMessage = this.elements.historyList.querySelector('.empty-message');
        if (emptyMessage) {
            emptyMessage.remove();
        }
        
        // 新しい履歴項目作成
        const punchType = Config.PUNCH_TYPES[punch.punch_type.toUpperCase()];
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <div class="history-time">
                ${Utils.formatDateTime(punch.punch_time, 'HH:mm')}
            </div>
            <div class="history-type">
                <span class="punch-type-badge ${punch.punch_type}">
                    ${punchType ? punchType.label : punch.punch_type}
                </span>
            </div>
        `;
        
        // リストの先頭に追加
        this.elements.historyList.insertBefore(historyItem, this.elements.historyList.firstChild);
    }

    /**
     * オンライン状態更新
     */
    updateOnlineStatus(isOnline) {
        if (isOnline) {
            this.elements.offlineBanner.style.display = 'none';
        } else {
            this.elements.offlineBanner.style.display = 'block';
        }
    }

    /**
     * ローディング表示
     */
    showLoading(show) {
        this.elements.loadingOverlay.style.display = show ? 'flex' : 'none';
    }

    /**
     * クリーンアップ
     */
    destroy() {
        // タイマークリア
        Object.values(this.timers).forEach(timer => {
            if (timer) {
                clearInterval(timer);
                clearTimeout(timer);
            }
        });
        
        // イベントリスナー解除
        this.elements.scanButton.removeEventListener('click', this.handleScanClick);
        this.elements.retryButton.removeEventListener('click', this.handleRetryClick);
    }
}

// グローバルに公開
window.UIController = UIController;