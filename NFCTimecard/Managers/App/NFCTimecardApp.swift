import SwiftUI

@main
struct NFCTimecardApp: App {
    @StateObject private var urlSchemeHandler = URLSchemeHandler()
    @StateObject private var sessionManager = SessionManager.shared
    
    init() {
        setupAppearance()
    }
    
    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(urlSchemeHandler)
                .environmentObject(sessionManager)
                .onOpenURL { url in
                    urlSchemeHandler.handleURL(url)
                }
        }
    }
    
    /// アプリ全体の外観設定
    private func setupAppearance() {
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

/// ルートビュー: ログイン状態に応じて画面を切り替える
///struct RootView: View {
    ///@EnvironmentObject private var sessionManager: SessionManager
    
   /// var body: some View {
        ///if sessionManager.isLoggedIn {
            ///ContentView()
        ///} else {
            ///LoginView()
        ///}
    ///}
///}
struct RootView: View {
    @EnvironmentObject private var sessionManager: SessionManager

    var body: some View {
        // いまは常にログイン画面を表示（開発用）
        LoginView()
    }
}
