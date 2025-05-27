import SwiftUI

@main
struct NFCTimecardApp: App {
    @StateObject private var urlSchemeHandler = URLSchemeHandler()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(urlSchemeHandler)
                .onOpenURL { url in
                    // カスタムURLスキームを処理
                    urlSchemeHandler.handleURL(url)
                }
        }
    }
}

// MARK: - アプリ設定
extension NFCTimecardApp {
    /// アプリ初期化処理
    init() {
        setupAppearance()
    }
    
    /// アプリ全体の外観設定
    private func setupAppearance() {
        // ナビゲーションバーの外観設定
        let appearance = UINavigationBarAppearance()
        appearance.configureWithOpaqueBackground()
        appearance.backgroundColor = UIColor.systemBackground
        appearance.titleTextAttributes = [.foregroundColor: UIColor.label]
        appearance.largeTitleTextAttributes = [.foregroundColor: UIColor.label]
        
        UINavigationBar.appearance().standardAppearance = appearance
        UINavigationBar.appearance().scrollEdgeAppearance = appearance
        UINavigationBar.appearance().compactAppearance = appearance
    }
}