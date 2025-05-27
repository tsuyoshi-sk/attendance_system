import Foundation
import SwiftUI
import Combine

// MARK: - URLSchemeHandler
/// カスタムURLスキームを処理するクラス
class URLSchemeHandler: ObservableObject {
    
    // MARK: - Published Properties
    @Published var isProcessing = false
    @Published var currentParameters: URLParameters?
    @Published var lastError: NFCError?
    @Published var shouldStartNFCReading = false
    
    // MARK: - Private Properties
    private var cancellables = Set<AnyCancellable>()
    
    // MARK: - Initialization
    init() {
        setupNotificationObservers()
    }
    
    // MARK: - Public Methods
    
    /// URLを処理
    /// - Parameter url: 処理するURL
    func handleURL(_ url: URL) {
        print("URL受信: \(url.absoluteString)")
        
        // スキームの確認
        guard url.scheme == URLScheme.SCHEME else {
            handleError(.invalidURL)
            return
        }
        
        // ホストの確認
        guard url.host == URLScheme.HOST else {
            handleError(.invalidURL)
            return
        }
        
        // パラメータの抽出
        guard let parameters = URLParameters(from: url) else {
            handleError(.missingParameters)
            return
        }
        
        // パラメータを保存
        currentParameters = parameters
        isProcessing = true
        lastError = nil
        
        // NFC読み取りを開始
        shouldStartNFCReading = true
        
        print("URLパラメータ解析成功: scanId=\(parameters.scanId), clientId=\(parameters.clientId)")
    }
    
    /// 処理をリセット
    func reset() {
        isProcessing = false
        currentParameters = nil
        lastError = nil
        shouldStartNFCReading = false
    }
    
    /// NFC読み取りを開始
    func startNFCReading() {
        guard let parameters = currentParameters else {
            handleError(.missingParameters)
            return
        }
        
        // NFCManagerに読み取りを依頼
        NFCManager.shared.startReading(with: parameters)
        
        // フラグをリセット
        shouldStartNFCReading = false
    }
    
    // MARK: - Private Methods
    
    /// 通知オブザーバーの設定
    private func setupNotificationObservers() {
        // API応答受信通知
        NotificationCenter.default.publisher(for: .apiResponseReceived)
            .sink { [weak self] notification in
                self?.handleAPIResponse(notification)
            }
            .store(in: &cancellables)
        
        // NFCスキャン失敗通知
        NotificationCenter.default.publisher(for: .nfcScanFailed)
            .sink { [weak self] notification in
                self?.handleNFCScanFailure(notification)
            }
            .store(in: &cancellables)
    }
    
    /// API応答の処理
    private func handleAPIResponse(_ notification: Notification) {
        guard let scanResult = notification.userInfo?["scanResult"] as? ScanResult else { return }
        
        DispatchQueue.main.async { [weak self] in
            self?.isProcessing = false
            
            // 成功した場合、PWAに自動的に戻る
            if scanResult.success {
                self?.returnToPWA()
            }
        }
    }
    
    /// NFCスキャン失敗の処理
    private func handleNFCScanFailure(_ notification: Notification) {
        guard let error = notification.userInfo?["error"] as? NFCError else { return }
        
        DispatchQueue.main.async { [weak self] in
            self?.lastError = error
            self?.isProcessing = false
        }
    }
    
    /// PWAに戻る
    private func returnToPWA() {
        // PWAのURLを開く（仮実装）
        if let url = URL(string: "\(API.BASE_URL)/pwa/scan-complete") {
            if UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url)
            }
        }
    }
    
    /// エラーハンドリング
    private func handleError(_ error: NFCError) {
        DispatchQueue.main.async { [weak self] in
            self?.lastError = error
            self?.isProcessing = false
            self?.shouldStartNFCReading = false
        }
    }
}

// MARK: - URLSchemeHandler Extension for Validation
extension URLSchemeHandler {
    
    /// URLスキームが有効かチェック
    /// - Parameter url: チェックするURL
    /// - Returns: 有効な場合true
    static func isValidURLScheme(_ url: URL) -> Bool {
        guard url.scheme == URLScheme.SCHEME else { return false }
        guard url.host == URLScheme.HOST else { return false }
        guard URLParameters(from: url) != nil else { return false }
        return true
    }
    
    /// デバッグ用URL生成
    static func generateDebugURL(scanId: String? = nil, clientId: String? = nil) -> URL? {
        let sid = scanId ?? "scan_\(Int(Date().timeIntervalSince1970 * 1000))_debug"
        let cid = clientId ?? "pwa_debug_\(UUID().uuidString.prefix(8))"
        
        var components = URLComponents()
        components.scheme = URLScheme.SCHEME
        components.host = URLScheme.HOST
        components.queryItems = [
            URLQueryItem(name: URLScheme.SCAN_ID_PARAM, value: sid),
            URLQueryItem(name: URLScheme.CLIENT_ID_PARAM, value: cid),
            URLQueryItem(name: URLScheme.CALLBACK_PARAM, value: "ws")
        ]
        
        return components.url
    }
}