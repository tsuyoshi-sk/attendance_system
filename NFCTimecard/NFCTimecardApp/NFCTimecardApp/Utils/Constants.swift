//
//  Constants.swift
//  NFCTimecardApp
//
//  Created by Tsuyoshi Sakai on 2025/11/17.
//

import Foundation

enum Constants {
    enum API {
        /// ベースURLはあとで FastAPI のURLに合わせて変更
        static let baseURL = URL(string: "http://127.0.0.1:8000")!
        static let scanResultPath = "/api/v1/nfc/scan-result"
    }
}
