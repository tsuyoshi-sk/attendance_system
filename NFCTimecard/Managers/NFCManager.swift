import Foundation
import CoreNFC
import Combine

// MARK: - NFCManager
/// NFC読み取り機能を管理するクラス
class NFCManager: NSObject, ObservableObject {
    
    // MARK: - Published Properties
    @Published var isReading = false
    @Published var lastError: NFCError?
    @Published var lastScanResult: ScanResult?
    
    // MARK: - Private Properties
    private var session: NFCTagReaderSession?
    private var currentParameters: URLParameters?
    private var readingTimer: Timer?
    private let apiClient = APIClient.shared
    
    // MARK: - Singleton
    static let shared = NFCManager()
    
    private override init() {
        super.init()
    }
    
    // MARK: - Public Methods
    
    /// NFC読み取りを開始
    /// - Parameter parameters: URLパラメータ
    func startReading(with parameters: URLParameters) {
        guard NFCTagReaderSession.readingAvailable else {
            handleError(.nfcNotAvailable, parameters: parameters)
            return
        }
        
        currentParameters = parameters
        isReading = true
        lastError = nil
        
        // セッションの作成
        session = NFCTagReaderSession(
            pollingOption: [.iso14443],
            delegate: self,
            queue: nil
        )
        
        session?.alertMessage = "Suicaをかざしてください"
        session?.begin()
        
        // タイムアウトタイマーの設定
        startTimeoutTimer()
    }
    
    /// 読み取りを中止
    func stopReading() {
        cancelTimeoutTimer()
        session?.invalidate()
        session = nil
        isReading = false
    }
    
    // MARK: - Private Methods
    
    /// タイムアウトタイマー開始
    private func startTimeoutTimer() {
        cancelTimeoutTimer()
        readingTimer = Timer.scheduledTimer(withTimeInterval: NFC.READ_TIMEOUT, repeats: false) { [weak self] _ in
            self?.handleTimeout()
        }
    }
    
    /// タイムアウトタイマーキャンセル
    private func cancelTimeoutTimer() {
        readingTimer?.invalidate()
        readingTimer = nil
    }
    
    /// タイムアウト処理
    private func handleTimeout() {
        if let params = currentParameters {
            handleError(.readTimeout, parameters: params)
        }
        stopReading()
    }
    
    /// エラーハンドリング
    private func handleError(_ error: NFCError, parameters: URLParameters) {
        DispatchQueue.main.async { [weak self] in
            self?.lastError = error
            self?.isReading = false
            
            // エラー結果をAPIに送信
            let scanResult = ScanResult.error(
                scanId: parameters.scanId,
                clientId: parameters.clientId,
                error: error
            )
            
            Task {
                await self?.apiClient.sendScanResult(scanResult)
            }
        }
    }
    
    /// Suica IDm の抽出とフォーマット
    private func extractSuicaIDm(from tag: NFCFeliCaTag) async throws -> String {
        // Polling
        let (idm, _) = try await tag.polling(
                systemCode: Data([0x00, 0x03]),
                requestCode: .systemCode,
                timeSlot: .max1
            )
        
        // IDmを16進数文字列に変換
        let idmHex = idm.map { String(format: "%02x", $0) }.joined()
        return "\(NFC.CARD_ID_PREFIX)\(idmHex)"
    }
}

// MARK: - NFCTagReaderSessionDelegate
extension NFCManager: NFCTagReaderSessionDelegate {
    
    func tagReaderSessionDidBecomeActive(_ session: NFCTagReaderSession) {
        // セッションがアクティブになった
    }
    
    func tagReaderSession(_ session: NFCTagReaderSession, didInvalidateWithError error: Error) {
        // セッションが無効化された
        DispatchQueue.main.async { [weak self] in
            self?.isReading = false
            self?.cancelTimeoutTimer()
            
            // キャンセル以外のエラーの場合
            if let nfcError = error as? NFCReaderError,
               nfcError.code != .readerSessionInvalidationErrorUserCanceled,
               let params = self?.currentParameters {
                
                let customError: NFCError
                switch nfcError.code {
                case .readerSessionInvalidationErrorSessionTimeout:
                    customError = .readTimeout
                case .readerSessionInvalidationErrorSessionTerminatedUnexpectedly:
                    customError = .unknownError(message: "セッションが予期せず終了しました")
                default:
                    customError = .unknownError(message: nfcError.localizedDescription)
                }
                
                self?.handleError(customError, parameters: params)
            }
        }
    }
    
    func tagReaderSession(_ session: NFCTagReaderSession, didDetect tags: [NFCTag]) {
        // 複数タグ検出チェック
        guard tags.count == 1 else {
            if let params = currentParameters {
                handleError(.multipleCardsDetected, parameters: params)
            }
            session.invalidate(errorMessage: ErrorMessage.MULTIPLE_CARDS_DETECTED)
            return
        }
        
        guard let tag = tags.first else { return }
        
        // FeliCaタグかチェック
        guard case .feliCa(let feliCaTag) = tag else {
            if let params = currentParameters {
                handleError(.unsupportedCard, parameters: params)
            }
            session.invalidate(errorMessage: ErrorMessage.UNSUPPORTED_CARD)
            return
        }
        
        // タグに接続
        Task {
            do {
                try await session.connect(to: tag)
                
                // Suica IDm を取得
                let cardId = try await extractSuicaIDm(from: feliCaTag)
                
                // 成功処理
                await handleSuccessfulScan(cardId: cardId, session: session)
                
            } catch {
                // エラー処理
                if let params = currentParameters {
                    handleError(.unknownError(message: error.localizedDescription), parameters: params)
                }
                session.invalidate(errorMessage: ErrorMessage.UNKNOWN_ERROR)
            }
        }
    }
    
    /// 読み取り成功時の処理
    private func handleSuccessfulScan(cardId: String, session: NFCTagReaderSession) async {
        guard let params = currentParameters else { return }
        
        cancelTimeoutTimer()
        
        // 成功メッセージ表示
        session.alertMessage = "読み取り成功！"
        
        // 結果を作成
        let scanResult = ScanResult(
            scanId: params.scanId,
            clientId: params.clientId,
            cardId: cardId,
            success: true
        )
        
        // 既存PWA連携への送信
        await apiClient.sendScanResult(scanResult)
        
        // FastAPI への打刻
        do {
            try await apiClient.postPunch(cardIdm: cardId, punchType: "in")
        } catch {
            await MainActor.run {
                self.lastError = error as? NFCError ?? .networkError(underlying: error)
            }
        }
        
        // UIを更新
        await MainActor.run {
            self.lastScanResult = scanResult
            self.isReading = false
        }
        
        // セッションを終了
        session.invalidate()
    }
}
