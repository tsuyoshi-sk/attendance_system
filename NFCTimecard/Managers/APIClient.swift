import Foundation
import Combine

// MARK: - APIClient
/// バックエンドとの通信を管理するクラス
class APIClient: ObservableObject {
    
    // MARK: - Published Properties
    @Published var isLoading = false
    @Published var lastError: NFCError?
    
    // MARK: - Private Properties
    private let session: URLSession
    private var cancellables = Set<AnyCancellable>()
    
    // MARK: - Singleton
    static let shared = APIClient()
    
    private init() {
        // URLSession設定
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = API.TIMEOUT_INTERVAL
        configuration.timeoutIntervalForResource = API.TIMEOUT_INTERVAL
        configuration.waitsForConnectivity = true
        
        self.session = URLSession(configuration: configuration)
    }
    
    // MARK: - Public Methods
    
    /// スキャン結果をバックエンドに送信
    /// - Parameter scanResult: スキャン結果
    func sendScanResult(_ scanResult: ScanResult) async {
        await sendScanResultWithRetry(scanResult, retryCount: 0)
    }
    
    // MARK: - Private Methods
    
    /// リトライ機能付きスキャン結果送信
    private func sendScanResultWithRetry(_ scanResult: ScanResult, retryCount: Int) async {
        // URLの構築
        guard let url = URL(string: "\(API.BASE_URL)\(API.NFC_SCAN_RESULT_ENDPOINT)") else {
            await handleError(.invalidURL)
            return
        }
        
        // リクエストの作成
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            // リクエストボディの設定
            request.httpBody = try scanResult.toJSONData()
            
            // ローディング状態を更新
            await MainActor.run {
                self.isLoading = true
            }
            
            // リクエスト実行
            let (data, response) = try await session.data(for: request)
            
            // レスポンス処理
            await handleResponse(data: data, response: response, scanResult: scanResult, retryCount: retryCount)
            
        } catch {
            // エラー処理
            if retryCount < API.MAX_RETRY_COUNT {
                // リトライ
                print("APIリクエスト失敗 (試行 \(retryCount + 1)/\(API.MAX_RETRY_COUNT)): \(error.localizedDescription)")
                
                // 指数バックオフでリトライ
                let delay = pow(2.0, Double(retryCount))
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                
                await sendScanResultWithRetry(scanResult, retryCount: retryCount + 1)
            } else {
                // リトライ上限に達した
                await handleError(.networkError(underlying: error))
            }
        }
        
        // ローディング状態を解除
        await MainActor.run {
            self.isLoading = false
        }
    }
    
    /// レスポンス処理
    private func handleResponse(data: Data, response: URLResponse, scanResult: ScanResult, retryCount: Int) async {
        guard let httpResponse = response as? HTTPURLResponse else {
            await handleError(.unknownError(message: "無効なレスポンス"))
            return
        }
        
        switch httpResponse.statusCode {
        case 200...299:
            // 成功
            print("API送信成功: scanId=\(scanResult.scanId)")
            await MainActor.run {
                self.lastError = nil
            }
            
            // 成功通知を送信
            NotificationCenter.default.post(
                name: .apiResponseReceived,
                object: nil,
                userInfo: ["scanResult": scanResult]
            )
            
        case 400...499:
            // クライアントエラー
            let errorMessage = extractErrorMessage(from: data)
            await handleError(.apiError(statusCode: httpResponse.statusCode, message: errorMessage))
            
        case 500...599:
            // サーバーエラー - リトライ可能
            if retryCount < API.MAX_RETRY_COUNT {
                print("サーバーエラー (ステータス: \(httpResponse.statusCode)) - リトライします")
                
                let delay = pow(2.0, Double(retryCount))
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                
                await sendScanResultWithRetry(scanResult, retryCount: retryCount + 1)
            } else {
                let errorMessage = extractErrorMessage(from: data)
                await handleError(.apiError(statusCode: httpResponse.statusCode, message: errorMessage))
            }
            
        default:
            // その他のステータスコード
            await handleError(.apiError(statusCode: httpResponse.statusCode, message: nil))
        }
    }
    
    /// エラーメッセージの抽出
    private func extractErrorMessage(from data: Data) -> String? {
        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let error = json["error"] as? [String: Any],
               let message = error["message"] as? String {
                return message
            }
        } catch {
            print("エラーメッセージの解析に失敗: \(error)")
        }
        return nil
    }
    
    /// エラーハンドリング
    private func handleError(_ error: NFCError) async {
        await MainActor.run {
            self.lastError = error
            self.isLoading = false
        }
        
        // エラー通知を送信
        NotificationCenter.default.post(
            name: .nfcScanFailed,
            object: nil,
            userInfo: ["error": error]
        )
    }
}

// MARK: - API Response Models
struct APIErrorResponse: Codable {
    let error: APIError
}

struct APIError: Codable {
    let message: String
    let statusCode: Int
    let details: [String: Any]?
    
    enum CodingKeys: String, CodingKey {
        case message
        case statusCode = "status_code"
        case details
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        message = try container.decode(String.self, forKey: .message)
        statusCode = try container.decode(Int.self, forKey: .statusCode)
        details = try? container.decode([String: Any].self, forKey: .details)
    }
}