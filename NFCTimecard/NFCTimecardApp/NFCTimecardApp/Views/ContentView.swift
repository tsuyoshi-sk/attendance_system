import SwiftUI

struct ContentView: View {
    @State private var employeeId: String = ""
    @State private var message: String = "社員IDを入力して打刻してください"
    @State private var isSubmitting = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()

                Text("NFCTimecard（NFCなし版）")
                    .font(.title.bold())

                TextField("社員ID", text: $employeeId)
                    .keyboardType(.numberPad)
                    .textInputAutocapitalization(.never)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(12)

                Button {
                    Task { await submitPunch() }
                } label: {
                    HStack {
                        if isSubmitting {
                            ProgressView()
                        }
                        Text("打刻する")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(employeeId.isEmpty ? Color.gray.opacity(0.5) : Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                .disabled(employeeId.isEmpty || isSubmitting)

                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                Spacer()
            }
            .padding()
            .navigationTitle("NFCTimecard")
        }
    }

    private func submitPunch() async {
        isSubmitting = true
        defer { isSubmitting = false }

        // TODO: FastAPI の URL に書き換える
        guard let url = URL(string: "http://127.0.0.1:8000/api/v1/punch") else {
            message = "URLが正しくありません"
            return
        }

        struct PunchRequest: Codable {
            let employeeId: String
        }

        let body = PunchRequest(employeeId: employeeId)

        do {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.addValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(body)

            let (_, response) = try await URLSession.shared.data(for: request)

            if let http = response as? HTTPURLResponse,
               (200..<300).contains(http.statusCode) {
                message = "社員ID \(employeeId) で打刻しました。"
            } else {
                message = "サーバー側でエラーが発生しました。"
            }
        } catch {
            message = "通信エラー：\(error.localizedDescription)"
        }
    }
}

#Preview {
    ContentView()
}
