import Foundation

// MARK: - NFC読み取り結果
struct ScanResult: Codable {
    let scanId: String
    let clientId: String
    let cardId: String
    let success: Bool
    let errorMessage: String?
    let timestamp: Int64
    
    /// 初期化
    init(scanId: String, clientId: String, cardId: String, success: Bool, errorMessage: String? = nil) {
        self.scanId = scanId
        self.clientId = clientId
        self.cardId = cardId
        self.success = success
        self.errorMessage = errorMessage
        self.timestamp = Int64(Date().timeIntervalSince1970 * 1000)
    }
    
    /// エラー結果の生成
    static func error(scanId: String, clientId: String, error: NFCError) -> ScanResult {
        return ScanResult(
            scanId: scanId,
            clientId: clientId,
            cardId: "",
            success: false,
            errorMessage: error.localizedDescription
        )
    }
}

// MARK: - API Request/Response
extension ScanResult {
    /// APIリクエスト用のJSON変換
    func toJSONData() throws -> Data {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return try encoder.encode(self)
    }
}

// MARK: - URLパラメータ
struct URLParameters {
    let scanId: String
    let clientId: String
    let callback: String?
    
    /// URL から パラメータを抽出
    init?(from url: URL) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let queryItems = components.queryItems else {
            return nil
        }
        
        var scanId: String?
        var clientId: String?
        var callback: String?
        
        for item in queryItems {
            switch item.name {
            case URLScheme.SCAN_ID_PARAM:
                scanId = item.value
            case URLScheme.CLIENT_ID_PARAM:
                clientId = item.value
            case URLScheme.CALLBACK_PARAM:
                callback = item.value
            default:
                break
            }
        }
        
        // 必須パラメータの確認
        guard let sid = scanId, let cid = clientId else {
            return nil
        }
        
        self.scanId = sid
        self.clientId = cid
        self.callback = callback
    }
}