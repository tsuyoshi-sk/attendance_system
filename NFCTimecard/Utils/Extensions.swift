import Foundation
import SwiftUI

// MARK: - View Extensions
extension View {
    /// カスタムコーナー半径を適用
    func customCornerRadius(_ radius: CGFloat = UI.CORNER_RADIUS) -> some View {
        self.clipShape(RoundedRectangle(cornerRadius: radius))
    }
    
    /// 標準パディングを適用
    func standardPadding() -> some View {
        self.padding(UI.PADDING_STANDARD)
    }
    
    /// 条件付きモディファイア
    @ViewBuilder
    func `if`<Content: View>(_ condition: Bool, transform: (Self) -> Content) -> some View {
        if condition {
            transform(self)
        } else {
            self
        }
    }
    
    /// エラーアラート表示
    func errorAlert(error: Binding<NFCError?>) -> some View {
        self.alert(
            "エラー",
            isPresented: .constant(error.wrappedValue != nil),
            presenting: error.wrappedValue
        ) { _ in
            Button("OK") {
                error.wrappedValue = nil
            }
        } message: { error in
            Text(error.localizedDescription)
        }
    }
}

// MARK: - Color Extensions
extension Color {
    /// アプリのプライマリカラー
    static let appPrimary = Color.blue
    
    /// アプリのセカンダリカラー
    static let appSecondary = Color.green
    
    /// エラーカラー
    static let appError = Color.red
    
    /// 成功カラー
    static let appSuccess = Color.green
    
    /// 背景カラー
    static let appBackground = Color(UIColor.systemBackground)
    
    /// セカンダリ背景カラー
    static let appSecondaryBackground = Color(UIColor.secondarySystemBackground)
}

// MARK: - String Extensions
extension String {
    /// 空文字列かどうか
    var isBlank: Bool {
        self.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
    
    /// 日付文字列をフォーマット
    func formattedDate() -> String? {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSZZZ"
        
        guard let date = formatter.date(from: self) else { return nil }
        
        formatter.dateStyle = .medium
        formatter.timeStyle = .medium
        formatter.locale = Locale(identifier: "ja_JP")
        
        return formatter.string(from: date)
    }
}

// MARK: - Date Extensions
extension Date {
    /// タイムスタンプ（ミリ秒）を取得
    var millisecondsSince1970: Int64 {
        Int64(self.timeIntervalSince1970 * 1000)
    }
    
    /// 日本語フォーマットで日時を取得
    func japaneseDateTimeString() -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .medium
        formatter.locale = Locale(identifier: "ja_JP")
        return formatter.string(from: self)
    }
}

// MARK: - Data Extensions
extension Data {
    /// 16進数文字列に変換
    var hexString: String {
        self.map { String(format: "%02x", $0) }.joined()
    }
}

// MARK: - Notification.Name Extensions
extension Notification {
    /// 通知からエラーを取得
    var nfcError: NFCError? {
        return userInfo?["error"] as? NFCError
    }
    
    /// 通知からスキャン結果を取得
    var scanResult: ScanResult? {
        return userInfo?["scanResult"] as? ScanResult
    }
}

// MARK: - UIApplication Extensions
extension UIApplication {
    /// 現在のキーウィンドウを取得
    var currentKeyWindow: UIWindow? {
        connectedScenes
            .filter { $0.activationState == .foregroundActive }
            .compactMap { $0 as? UIWindowScene }
            .first?.windows
            .filter { $0.isKeyWindow }
            .first
    }
    
    /// ルートビューコントローラーを取得
    var rootViewController: UIViewController? {
        currentKeyWindow?.rootViewController
    }
}

// MARK: - ViewModifier for Loading Overlay
struct LoadingOverlay: ViewModifier {
    let isLoading: Bool
    let message: String
    
    func body(content: Content) -> some View {
        ZStack {
            content
                .disabled(isLoading)
                .blur(radius: isLoading ? 3 : 0)
            
            if isLoading {
                VStack(spacing: 20) {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle())
                        .scaleEffect(1.5)
                    
                    Text(message)
                        .font(.headline)
                        .foregroundColor(.primary)
                }
                .padding(40)
                .background(Color.appSecondaryBackground)
                .customCornerRadius()
                .shadow(radius: 10)
            }
        }
    }
}

extension View {
    /// ローディングオーバーレイを表示
    func loadingOverlay(isLoading: Bool, message: String = "処理中...") -> some View {
        self.modifier(LoadingOverlay(isLoading: isLoading, message: message))
    }
}