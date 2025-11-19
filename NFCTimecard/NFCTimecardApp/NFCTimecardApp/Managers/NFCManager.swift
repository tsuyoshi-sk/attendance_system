import Foundation
import CoreNFC

@MainActor
final class NFCManager: NSObject {
    static let shared = NFCManager()
    private override init() {}

    private var session: NFCTagReaderSession?
    private var completion: ((Result<ScanResult, NFCError>) -> Void)?

    private var currentScanId: String = ""
    private var currentClientId: String = ""

    func startScan(
        scanId: String,
        clientId: String,
        completion: @escaping (Result<ScanResult, NFCError>) -> Void
    ) {
        guard NFCTagReaderSession.readingAvailable else {
            completion(.failure(.nfcNotAvailable))
            return
        }

        self.currentScanId = scanId
        self.currentClientId = clientId
        self.completion = completion

        // Suica = Felica (iso18092)
        guard let newSession = NFCTagReaderSession(
            pollingOption: .iso18092,
            delegate: self,
            queue: nil
        ) else {
            completion(.failure(.nfcNotAvailable))
            return
        }

        newSession.alertMessage = "iPhone上部をSuicaに近づけてください。"
        newSession.begin()

        self.session = newSession

    }

    private func finish(
        with result: Result<ScanResult, NFCError>,
        invalidateSession message: String? = nil
    ) {
        if let message {
            session?.invalidate(errorMessage: message)
        } else {
            session?.invalidate()
        }
        session = nil

        completion?(result)
        completion = nil
    }
}

extension NFCManager: NFCTagReaderSessionDelegate {
    func tagReaderSessionDidBecomeActive(_ session: NFCTagReaderSession) {
        // 何もしなくてOK
    }

    func tagReaderSession(_ session: NFCTagReaderSession, didInvalidateWithError error: Error) {
        if let nfcError = error as? NFCReaderError,
           nfcError.code == .readerSessionInvalidationErrorUserCanceled {
            finish(with: .failure(.sessionInvalidated(message: "読み取りがキャンセルされました。")))
        } else {
            finish(with: .failure(.sessionInvalidated(message: error.localizedDescription)))
        }
    }

    func tagReaderSession(_ session: NFCTagReaderSession, didDetect tags: [NFCTag]) {
        // 複数検出
        if tags.count > 1 {
            finish(with: .failure(.multipleCardsDetected),
                   invalidateSession: "複数のカードが検出されました。1枚だけかざしてください。")
            return
        }

        guard let firstTag = tags.first else {
            finish(with: .failure(.readTimeout),
                   invalidateSession: "カードを検出できませんでした。")
            return
        }

        // ★ ここポイント：.feliCa（Cが大文字）
        guard case let .feliCa(felicaTag) = firstTag else {
            finish(with: .failure(.unsupportedCard),
                   invalidateSession: "Suica以外のカードが検出されました。")
            return
        }

        session.connect(to: firstTag) { [weak self] error in
            guard let self else { return }

            if let error {
                self.finish(with: .failure(.sessionInvalidated(message: error.localizedDescription)),
                            invalidateSession: "読み取りに失敗しました。")
                return
            }

            let idmData = felicaTag.currentIDm
            let idmString = idmData.map { String(format: "%02X", $0) }.joined()

            let result = ScanResult(
                scanId: self.currentScanId,
                clientId: self.currentClientId,
                idm: idmString
            )

            self.finish(with: .success(result))
        }
    }
}
