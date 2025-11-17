import Foundation
import Combine

/// JWT を保持し、ログイン状態を管理するクラス
final class SessionManager: ObservableObject {
    static let shared = SessionManager()
    
    @Published private(set) var isLoggedIn: Bool = false
    @Published private(set) var accessToken: String?
    
    private let usernameKey = "nfctimecard.username"
    private let tokenKey = "nfctimecard.token"
    private let keychain = KeychainHelper.shared
    
    private init() {
        if let tokenData = keychain.read(for: tokenKey),
           let token = String(data: tokenData, encoding: .utf8) {
            self.accessToken = token
            self.isLoggedIn = true
        }
    }
    
    /// ログインAPIを叩き、トークンを保存
    func login(username: String, password: String) async throws {
        let requestBody = LoginRequest(username: username, password: password)
        let url = URL(string: "\(API.BASE_URL)\(API.Endpoint.login)")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = requestBody.formURLEncoded.data(using: .utf8)
        
        let (data, response) = try await APIClient.shared.perform(request, requiresAuth: false)
        
        guard let httpResponse = response as? HTTPURLResponse,
              200..<300 ~= httpResponse.statusCode else {
            throw NFCError.apiError(statusCode: (response as? HTTPURLResponse)?.statusCode ?? -1, message: "ログインに失敗しました")
        }
        
        let decoder = JSONDecoder()
        let loginResponse = try decoder.decode(LoginResponse.self, from: data)
        await MainActor.run {
            storeToken(loginResponse.accessToken, username: username)
        }
    }
    
    /// ログアウトしてトークンを削除
    func logout() {
        keychain.delete(for: tokenKey)
        UserDefaults.standard.removeObject(forKey: usernameKey)
        accessToken = nil
        isLoggedIn = false
    }
    
    private func storeToken(_ token: String, username: String) {
        accessToken = token
        isLoggedIn = true
        keychain.save(Data(token.utf8), for: tokenKey)
        UserDefaults.standard.setValue(username, forKey: usernameKey)
    }
}

// MARK: - Request / Response DTO
private struct LoginRequest {
    let username: String
    let password: String
    
    var formURLEncoded: String {
        "username=\(username.urlEncoded)&password=\(password.urlEncoded)"
    }
}

struct LoginResponse: Decodable {
    let accessToken: String
    let tokenType: String
    
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}

private extension String {
    var urlEncoded: String {
        addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? self
    }
}
