import SwiftUI
import Combine

struct ContentView: View {
    // MARK: - Environment & State
    @EnvironmentObject var urlSchemeHandler: URLSchemeHandler
    @StateObject private var nfcManager = NFCManager.shared
    @StateObject private var apiClient = APIClient.shared
    
    @State private var showingNFCScan = false
    @State private var showingSuccess = false
    @State private var successMessage = ""
    @State private var debugMode = false
    
    // MARK: - Body
    var body: some View {
        NavigationView {
            ZStack {
                // 背景グラデーション
                LinearGradient(
                    gradient: Gradient(colors: [Color.appPrimary.opacity(0.1), Color.appSecondary.opacity(0.1)]),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()
                
                VStack(spacing: 30) {
                    // ヘッダー
                    headerView
                    
                    Spacer()
                    
                    // メインコンテンツ
                    if urlSchemeHandler.isProcessing || nfcManager.isReading {
                        nfcReadingView
                    } else if showingSuccess {
                        successView
                    } else {
                        waitingView
                    }
                    
                    Spacer()
                    
                    // デバッグボタン（開発時のみ）
                    #if DEBUG
                    debugSection
                    #endif
                }
                .standardPadding()
            }
            .navigationBarHidden(true)
            .errorAlert(error: Binding(
                get: { urlSchemeHandler.lastError ?? nfcManager.lastError },
                set: { _ in
                    urlSchemeHandler.lastError = nil
                    nfcManager.lastError = nil
                }
            ))
            .loadingOverlay(isLoading: apiClient.isLoading, message: "送信中...")
            .onChange(of: urlSchemeHandler.shouldStartNFCReading) { shouldStart in
                if shouldStart {
                    showingNFCScan = true
                    urlSchemeHandler.startNFCReading()
                }
            }
            .onChange(of: nfcManager.lastScanResult) { result in
                if let result = result, result.success {
                    handleSuccessfulScan(result)
                }
            }
            .fullScreenCover(isPresented: $showingNFCScan) {
                NFCScanView()
                    .environmentObject(nfcManager)
                    .environmentObject(urlSchemeHandler)
            }
        }
    }
    
    // MARK: - View Components
    
    /// ヘッダービュー
    private var headerView: some View {
        VStack(spacing: 10) {
            Image(systemName: "clock.badge.checkmark.fill")
                .font(.system(size: 60))
                .foregroundColor(.appPrimary)
            
            Text("NFC勤怠管理")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Text("iPhone Suica対応")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
    }
    
    /// 待機中ビュー
    private var waitingView: some View {
        VStack(spacing: 20) {
            Image(systemName: "iphone.radiowaves.left.and.right")
                .font(.system(size: 80))
                .foregroundColor(.gray)
                .opacity(0.5)
            
            Text("PWAからの起動を待機中...")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Text("勤怠管理システムから\n「NFCスキャン開始」をタップしてください")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(40)
    }
    
    /// NFC読み取り中ビュー
    private var nfcReadingView: some View {
        VStack(spacing: 30) {
            // アニメーション
            ZStack {
                Circle()
                    .stroke(Color.appPrimary.opacity(0.3), lineWidth: 4)
                    .frame(width: 150, height: 150)
                
                Circle()
                    .stroke(Color.appPrimary, lineWidth: 4)
                    .frame(width: 150, height: 150)
                    .scaleEffect(nfcManager.isReading ? 1.2 : 1.0)
                    .opacity(nfcManager.isReading ? 0.0 : 1.0)
                    .animation(
                        nfcManager.isReading ?
                        Animation.easeOut(duration: 1.0).repeatForever(autoreverses: false) :
                        .default,
                        value: nfcManager.isReading
                    )
                
                Image(systemName: "creditcard.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.appPrimary)
            }
            
            Text("Suicaをかざしてください")
                .font(.title2)
                .fontWeight(.semibold)
            
            if let params = urlSchemeHandler.currentParameters {
                VStack(spacing: 5) {
                    Text("スキャンID: \(params.scanId)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
    }
    
    /// 成功ビュー
    private var successView: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 80))
                .foregroundColor(.appSuccess)
                .transition(.scale.combined(with: .opacity))
            
            Text("読み取り成功！")
                .font(.title)
                .fontWeight(.bold)
            
            Text(successMessage)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(40)
        .onAppear {
            // 2秒後に自動的にPWAに戻る
            DispatchQueue.main.asyncAfter(deadline: .now() + UI.SUCCESS_DISPLAY_DURATION) {
                withAnimation {
                    showingSuccess = false
                    successMessage = ""
                }
                urlSchemeHandler.reset()
            }
        }
    }
    
    /// デバッグセクション
    private var debugSection: some View {
        VStack(spacing: 15) {
            Toggle("デバッグモード", isOn: $debugMode)
                .toggleStyle(SwitchToggleStyle(tint: .appPrimary))
            
            if debugMode {
                VStack(spacing: 10) {
                    Button(action: testNFCScan) {
                        Label("テスト: NFC読み取り", systemImage: "square.and.arrow.down")
                    }
                    .buttonStyle(DebugButtonStyle())
                    
                    Button(action: testURLScheme) {
                        Label("テスト: URLスキーム", systemImage: "link")
                    }
                    .buttonStyle(DebugButtonStyle())
                }
            }
        }
        .padding()
        .background(Color.appSecondaryBackground)
        .customCornerRadius()
    }
    
    // MARK: - Methods
    
    /// 成功したスキャンを処理
    private func handleSuccessfulScan(_ result: ScanResult) {
        withAnimation(.easeInOut) {
            successMessage = "カードID: \(result.cardId)\n送信完了"
            showingSuccess = true
            showingNFCScan = false
        }
        
        // 触覚フィードバック
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
    }
    
    /// NFCスキャンテスト
    private func testNFCScan() {
        guard let debugURL = URLSchemeHandler.generateDebugURL() else { return }
        urlSchemeHandler.handleURL(debugURL)
    }
    
    /// URLスキームテスト
    private func testURLScheme() {
        let testURL = "nfc-timecard://scan?scan_id=test_123&client_id=debug_client&callback=ws"
        if let url = URL(string: testURL) {
            UIApplication.shared.open(url)
        }
    }
}

// MARK: - Button Styles
struct DebugButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.footnote)
            .foregroundColor(.white)
            .padding(.horizontal, 20)
            .padding(.vertical, 10)
            .background(configuration.isPressed ? Color.gray : Color.appPrimary)
            .customCornerRadius(8)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
    }
}

// MARK: - Preview
struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
            .environmentObject(URLSchemeHandler())
            .previewDevice("iPhone 13")
    }
}