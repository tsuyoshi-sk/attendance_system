//
//  Scanresult.swift
//  NFCTimecardApp
//
//  Created by Tsuyoshi Sakai on 2025/11/17.
//

import Foundation

struct ScanResult: Codable {
    let scanId: String
    let clientId: String
    let idm: String
}
