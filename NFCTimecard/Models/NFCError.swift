import Foundation

// MARK: - NFCエラー定義
enum NFCError: Error {
    case nfcNotAvailable
    case nfcDisabled
    case multipleCardsDetected
    case readTimeout
    case unsupportedCard
    case networkError(underlying: Error?)
    case unknownError(message: String?)
    case invalidURL
    case missingParameters
    case apiError(statusCode: Int, message: String?)
    
    /// ユーザー向けエラーメッセージ
    var localizedDescription: String {
        switch self {
        case .nfcNotAvailable:
            return ErrorMessage.NFC_NOT_AVAILABLE
        case .nfcDisabled:
            return ErrorMessage.NFC_DISABLED
        case .multipleCardsDetected:
            return ErrorMessage.MULTIPLE_CARDS_DETECTED
        case .readTimeout:
            return ErrorMessage.READ_TIMEOUT
        case .unsupportedCard:
            return ErrorMessage.UNSUPPORTED_CARD
        case .networkError(let underlying):
            if let error = underlying {
                return "\(ErrorMessage.NETWORK_ERROR): \(error.localizedDescription)"
            }
            return ErrorMessage.NETWORK_ERROR
        case .unknownError(let message):
            if let msg = message {
                return "\(ErrorMessage.UNKNOWN_ERROR): \(msg)"
            }
            return ErrorMessage.UNKNOWN_ERROR
        case .invalidURL:
            return ErrorMessage.INVALID_URL
        case .missingParameters:
            return ErrorMessage.MISSING_PARAMETERS
        case .apiError(let statusCode, let message):
            if let msg = message {
                return "APIエラー (\(statusCode)): \(msg)"
            }
            return "APIエラー: ステータスコード \(statusCode)"
        }
    }
    
    /// リトライ可能かどうか
    var isRetryable: Bool {
        switch self {
        case .networkError, .readTimeout, .apiError:
            return true
        default:
            return false
        }
    }
}