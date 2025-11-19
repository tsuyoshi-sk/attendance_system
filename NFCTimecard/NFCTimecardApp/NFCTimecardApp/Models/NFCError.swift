//
//  NFCError.swift
//  NFCTimecardApp
//
//  Created by Tsuyoshi Sakai on 2025/11/17.
//

import Foundation

enum NFCError: Error, LocalizedError {
    case nfcNotAvailable
    case multipleCardsDetected
    case readTimeout
    case unsupportedCard
    case sessionInvalidated(message: String)
    case networkError(underlying: Error)
    case apiError(statusCode: Int?)

    var errorDescription: String? {
        switch self {
        case .nfcNotAvailable:
            return "この端末ではNFCが利用できません。"
        case .multipleCardsDetected:
            return "複数のカードが検出されました。1枚だけかざしてください。"
        case .readTimeout:
            return "カードの読み取りがタイムアウトしました。"
        case .unsupportedCard:
            return "対応していないカードです。（Suicaのみ対応）"
        case .sessionInvalidated(let message):
            return message
        case .networkError:
            return "ネットワークエラーが発生しました。通信環境を確認してください。"
        case .apiError:
            return "サーバーとの通信でエラーが発生しました。"
        }
    }
}
