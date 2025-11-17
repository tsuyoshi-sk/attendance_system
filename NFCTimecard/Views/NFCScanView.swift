import SwiftUI

@available(iOS 15.0, *)
struct NFCScanView: View {
    // MARK: - Environment & State
    @EnvironmentObject var nfcManager: NFCManager
    @EnvironmentObject var urlSchemeHandler: URLSchemeHandler
    @Environment(\.dismiss) var dismiss
    
    @State private var animationScale: CGFloat = 1.0
    @State private var animationOpacity: Double = 1.0
    
    // MARK: - Body
    var body: some View {
        ZStack {
            // 背景
            Color.black.opacity(0.9)
                .ignoresSafeArea()
            
            VStack(spacing: 40) {
                // 閉じるボタン
                HStack {
                    Spacer()
                    Button(action: cancelScan) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 30))
                            .foregroundColor(.white.opacity(0.7))
                    }
                }
                .padding()
                
                Spacer()
                
                // NFCアニメーション
                nfcAnimationView
                
                // インストラクション
                instructionView
                
                Spacer()
                
                // キャンセルボタン
                Button(action: cancelScan) {
                    Text("キャンセル")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.red.opacity(0.8))
                        .customCornerRadius()
                }
                .padding(.horizontal, 40)
                .padding(.bottom, 40)
            }
        }
        .onAppear {
            startAnimation()
        }
        .onReceive(nfcManager.$lastError) { error in
            // error が nil じゃない時だけ閉じる
            guard error != nil else { return }
                // エラー時は自動的に閉じる
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                    dismiss()
                }
            }
        
        .onReceive(nfcManager.$lastScanResult) { result in
            guard let result = result, result.success else { return }

            if result.success == true {
                // 成功時は自動的に閉じる
                dismiss()
            }
        }
    }
    
    // MARK: - View Components
    
    /// NFCアニメーションビュー
    private var nfcAnimationView: some View {
        ZStack {
            // 外側のリング（アニメーション）
            ForEach(0..<3) { index in
                Circle()
                    .stroke(
                        LinearGradient(
                            gradient: Gradient(colors: [Color.blue, Color.cyan]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 2
                    )
                    .frame(width: 200 + CGFloat(index) * 50, height: 200 + CGFloat(index) * 50)
                    .scaleEffect(animationScale)
                    .opacity(animationOpacity - Double(index) * 0.3)
                    .animation(
                        Animation.easeInOut(duration: 2.0)
                            .repeatForever(autoreverses: true)
                            .delay(Double(index) * 0.2),
                        value: animationScale
                    )
            }
            
            // 中央のアイコン
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [Color.blue.opacity(0.8), Color.cyan.opacity(0.8)]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 150, height: 150)
                
                VStack(spacing: 10) {
                    Image(systemName: "wave.3.right")
                        .font(.system(size: 40))
                        .foregroundColor(.white)
                    
                    Image(systemName: "creditcard.fill")
                        .font(.system(size: 50))
                        .foregroundColor(.white)
                }
            }
            .shadow(color: .blue.opacity(0.5), radius: 20)
        }
    }
    
    /// インストラクションビュー
    private var instructionView: some View {
        VStack(spacing: 20) {
            Text("Suicaをかざしてください")
                .font(.title)
                .fontWeight(.bold)
                .foregroundColor(.white)
            
            Text("iPhoneの上部にカードを近づけてください")
                .font(.subheadline)
                .foregroundColor(.white.opacity(0.8))
                .multilineTextAlignment(.center)
            
            // ステータス表示
            if nfcManager.isReading {
                HStack(spacing: 8) {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.8)
                    
                    Text("読み取り中...")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.8))
                }
                .padding(.top, 10)
            }
        }
        .padding(.horizontal, 40)
    }
    
    // MARK: - Methods
    
    /// アニメーション開始
    private func startAnimation() {
        withAnimation {
            animationScale = 1.3
            animationOpacity = 0.3
        }
    }
    
    /// スキャンキャンセル
    private func cancelScan() {
        nfcManager.stopReading()
        dismiss()
    }
}

// MARK: - Success Animation View
struct SuccessAnimationView: View {
    @State private var checkmarkScale: CGFloat = 0.0
    @State private var checkmarkOpacity: Double = 0.0
    
    var body: some View {
        ZStack {
            Circle()
                .fill(Color.green.opacity(0.2))
                .frame(width: 200, height: 200)
                .scaleEffect(checkmarkScale)
                .opacity(checkmarkOpacity)
            
            Circle()
                .stroke(Color.green, lineWidth: 4)
                .frame(width: 200, height: 200)
                .scaleEffect(checkmarkScale)
                .opacity(checkmarkOpacity)
            
            Image(systemName: "checkmark")
                .font(.system(size: 80, weight: .bold))
                .foregroundColor(.green)
                .scaleEffect(checkmarkScale)
                .opacity(checkmarkOpacity)
        }
        .onAppear {
            withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
                checkmarkScale = 1.0
                checkmarkOpacity = 1.0
            }
        }
    }
}

// MARK: - Error Animation View
struct ErrorAnimationView: View {
    @State private var shakeOffset: CGFloat = 0.0
    let error: NFCError
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 80))
                .foregroundColor(.red)
                .offset(x: shakeOffset)
            
            Text("エラー")
                .font(.title)
                .fontWeight(.bold)
                .foregroundColor(.white)
            
            Text(error.localizedDescription)
                .font(.body)
                .foregroundColor(.white.opacity(0.8))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
        }
        .onAppear {
            withAnimation(.default.repeatCount(3).speed(3)) {
                shakeOffset = -10
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                shakeOffset = 0
            }
        }
    }
}

// MARK: - Preview
struct NFCScanView_Previews: PreviewProvider {
    static var previews: some View {
        NFCScanView()
            .environmentObject(NFCManager.shared)
            .environmentObject(URLSchemeHandler())
    }
}
