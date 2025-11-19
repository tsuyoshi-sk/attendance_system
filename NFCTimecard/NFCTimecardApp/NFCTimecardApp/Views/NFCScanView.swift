//
//  NFCScanView.swift
//  NFCTimecardApp
//
//  Created by Tsuyoshi Sakai on 2025/11/17.
//

import SwiftUI

struct NFCScanView: View {
    let scanId: String
    let clientId: String

    @State private var statusMessage: String = "「読み取り開始」ボタンを押して、Suicaをかざしてください。"
    @State private var isScanning: Bool = false
    @State private var errorMessage: String?
    @State private var idm: String?

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Text("NFC タイムカード")
                .font(.largeTitle.bold())

            Text(statusMessage)
                .font(.body)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            if let idm {
                Text("IDm: \(idm)")
                    .font(.footnote.monospaced())
                    .foregroundStyle(.secondary)
            }

            if let errorMessage {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }

            Button {
                startScan()
            } label: {
                HStack {
                    if isScanning {
                        ProgressView()
                    }
                    Text(isScanning ? "読み取り中..." : "読み取り開始")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(isScanning ? Color.gray.opacity(0.5) : Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .disabled(isScanning)

            Spacer()
        }
        .padding()
    }

    private func startScan() {
        errorMessage = nil
        idm = nil
        statusMessage = "Suicaをかざしてください。"
        isScanning = true

        NFCManager.shared.startScan(scanId: scanId, clientId: clientId) { result in
            Task { @MainActor in
                isScanning = false

                switch result {
                case .success(let scanResult):
                    idm = scanResult.idm
                    statusMessage = "読み取り成功。サーバーに送信中..."

                    await sendToAPI(scanResult)

                case .failure(let error):
                    errorMessage = error.localizedDescription
                    statusMessage = "読み取りに失敗しました。"
                }
            }
        }
    }

    private func sendToAPI(_ result: ScanResult) async {
        do {
            try await APIClient.shared.sendScanResult(result)
            statusMessage = "サーバーへの送信が完了しました。"
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            statusMessage = "サーバー送信に失敗しました。"
        }
    }
}

#Preview {
    NFCScanView(scanId: "debug_scan", clientId: "debug_client")
}
