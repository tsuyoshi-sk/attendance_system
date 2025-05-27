import Foundation

// MARK: - API設定
enum API {
    static let BASE_URL = "http://localhost:8000"
    static let NFC_SCAN_RESULT_ENDPOINT = "/api/v1/nfc/scan-result"
    static let TIMEOUT_INTERVAL: TimeInterval = 30.0
    static let MAX_RETRY_COUNT = 3
}

// MARK: - NFC設定
enum NFC {
    static let SUICA_SYSTEM_CODE: UInt16 = 0x0003
    static let READ_TIMEOUT: TimeInterval = 3.0
    static let CARD_ID_PREFIX = "suica_"
}

// MARK: - URLスキーム設定
enum URLScheme {
    static let SCHEME = "nfc-timecard"
    static let HOST = "scan"
    static let SCAN_ID_PARAM = "scan_id"
    static let CLIENT_ID_PARAM = "client_id"
    static let CALLBACK_PARAM = "callback"
}

// MARK: - エラーメッセージ
enum ErrorMessage {
    static let NFC_NOT_AVAILABLE = "NFC機能が利用できません"
    static let NFC_DISABLED = "NFC機能を有効にしてください"
    static let MULTIPLE_CARDS_DETECTED = "複数のカードが検出されました。1枚だけかざしてください"
    static let READ_TIMEOUT = "読み取りがタイムアウトしました。再度お試しください"
    static let UNSUPPORTED_CARD = "対応していないカードです"
    static let NETWORK_ERROR = "ネットワークエラーが発生しました"
    static let UNKNOWN_ERROR = "不明なエラーが発生しました"
    static let INVALID_URL = "無効なURLです"
    static let MISSING_PARAMETERS = "必要なパラメータが不足しています"
}

// MARK: - UI設定
enum UI {
    static let CORNER_RADIUS: CGFloat = 12.0
    static let PADDING_STANDARD: CGFloat = 16.0
    static let ANIMATION_DURATION: Double = 0.3
    static let SUCCESS_DISPLAY_DURATION: Double = 2.0
}

// MARK: - 通知名
extension Notification.Name {
    static let nfcScanCompleted = Notification.Name("nfcScanCompleted")
    static let nfcScanFailed = Notification.Name("nfcScanFailed")
    static let apiResponseReceived = Notification.Name("apiResponseReceived")
}