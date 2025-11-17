import SwiftUI

struct LoginView: View {
    @EnvironmentObject private var sessionManager: SessionManager
    
    @State private var username: String = ""
    @State private var password: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                VStack(spacing: 8) {
                    Image(systemName: "lock.shield.fill")
                        .font(.system(size: 56))
                        .foregroundColor(.appPrimary)
                    
                    Text("勤怠管理にログイン")
                        .font(.title2)
                        .fontWeight(.semibold)
                }
                .padding(.top, 40)
                
                VStack(spacing: 16) {
                    usernameField
                    SecureField("パスワード", text: $password)
                        .padding()
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(10)
                }
                
                if let errorMessage {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)
                }
                
                Button(action: login) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        }
                        Text(isLoading ? "ログイン中..." : "ログイン")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(isLoginEnabled ? Color.appPrimary : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                .disabled(!isLoginEnabled || isLoading)
                
                Spacer()
            }
            .padding()
            .navigationBarHidden(true)
        }
    }
    
    private var isLoginEnabled: Bool {
        !username.isEmpty && !password.isEmpty
    }
    
    private func login() {
        guard isLoginEnabled else {
            errorMessage = "ユーザー名とパスワードを入力してください"
            return
        }
        
        errorMessage = nil
        isLoading = true
        
        Task {
            do {
                try await sessionManager.login(username: username, password: password)
            } catch let error as NFCError {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                }
            } catch {
                await MainActor.run {
                    errorMessage = "ログインに失敗しました: \(error.localizedDescription)"
                }
            }
            
            await MainActor.run {
                isLoading = false
            }
        }
    }
}

private extension LoginView {
    @ViewBuilder
    var usernameField: some View {
        if #available(iOS 15.0, *) {
            TextField("ユーザー名", text: $username)
                .textInputAutocapitalization(.never)
                .disableAutocorrection(true)
                .padding()
                .background(Color(.secondarySystemBackground))
                .cornerRadius(10)
        } else {
            TextField("ユーザー名", text: $username)
                .autocapitalization(.none)
                .disableAutocorrection(true)
                .padding()
                .background(Color(.secondarySystemBackground))
                .cornerRadius(10)
        }
    }
}
