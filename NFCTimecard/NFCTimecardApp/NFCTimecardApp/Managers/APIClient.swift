//
//  APIClient.swift
//  NFCTimecardApp
//
//  Created by Tsuyoshi Sakai on 2025/11/17.
//

import Foundation

final class APIClient {
    static let shared = APIClient()
    private init() {}

    func sendScanResult(_ result: ScanResult) async throws {
        let url = Constants.API.baseURL.appendingPathComponent(Constants.API.scanResultPath)

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(result)

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse,
                  (200..<300).contains(http.statusCode) else {
                throw NFCError.apiError(statusCode: (response as? HTTPURLResponse)?.statusCode)
            }
        } catch {
            throw NFCError.networkError(underlying: error)
        }
    }
}
