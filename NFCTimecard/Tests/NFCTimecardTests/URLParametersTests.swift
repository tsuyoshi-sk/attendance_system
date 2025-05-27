import XCTest
@testable import NFCTimecard

final class URLParametersTests: XCTestCase {
    
    func testValidURLParsing() {
        // Given
        let urlString = "nfc-timecard://scan?scan_id=test123&client_id=client456&callback=ws"
        guard let url = URL(string: urlString) else {
            XCTFail("URLの作成に失敗")
            return
        }
        
        // When
        let parameters = URLParameters(from: url)
        
        // Then
        XCTAssertNotNil(parameters)
        XCTAssertEqual(parameters?.scanId, "test123")
        XCTAssertEqual(parameters?.clientId, "client456")
        XCTAssertEqual(parameters?.callback, "ws")
    }
    
    func testMissingRequiredParameters() {
        // Given - scan_idが欠けている
        let urlString = "nfc-timecard://scan?client_id=client456&callback=ws"
        guard let url = URL(string: urlString) else {
            XCTFail("URLの作成に失敗")
            return
        }
        
        // When
        let parameters = URLParameters(from: url)
        
        // Then
        XCTAssertNil(parameters)
    }
    
    func testOptionalCallbackParameter() {
        // Given - callbackパラメータなし
        let urlString = "nfc-timecard://scan?scan_id=test123&client_id=client456"
        guard let url = URL(string: urlString) else {
            XCTFail("URLの作成に失敗")
            return
        }
        
        // When
        let parameters = URLParameters(from: url)
        
        // Then
        XCTAssertNotNil(parameters)
        XCTAssertEqual(parameters?.scanId, "test123")
        XCTAssertEqual(parameters?.clientId, "client456")
        XCTAssertNil(parameters?.callback)
    }
}

final class ScanResultTests: XCTestCase {
    
    func testSuccessfulScanResult() {
        // Given
        let scanId = "scan_123"
        let clientId = "client_456"
        let cardId = "suica_0123456789abcdef"
        
        // When
        let result = ScanResult(
            scanId: scanId,
            clientId: clientId,
            cardId: cardId,
            success: true
        )
        
        // Then
        XCTAssertEqual(result.scanId, scanId)
        XCTAssertEqual(result.clientId, clientId)
        XCTAssertEqual(result.cardId, cardId)
        XCTAssertTrue(result.success)
        XCTAssertNil(result.errorMessage)
        XCTAssertGreaterThan(result.timestamp, 0)
    }
    
    func testErrorScanResult() {
        // Given
        let error = NFCError.nfcNotAvailable
        
        // When
        let result = ScanResult.error(
            scanId: "scan_123",
            clientId: "client_456",
            error: error
        )
        
        // Then
        XCTAssertFalse(result.success)
        XCTAssertEqual(result.cardId, "")
        XCTAssertEqual(result.errorMessage, error.localizedDescription)
    }
    
    func testJSONEncoding() throws {
        // Given
        let result = ScanResult(
            scanId: "scan_123",
            clientId: "client_456",
            cardId: "suica_test",
            success: true
        )
        
        // When
        let jsonData = try result.toJSONData()
        let json = try JSONSerialization.jsonObject(with: jsonData) as? [String: Any]
        
        // Then
        XCTAssertNotNil(json)
        XCTAssertEqual(json?["scan_id"] as? String, "scan_123")
        XCTAssertEqual(json?["client_id"] as? String, "client_456")
        XCTAssertEqual(json?["card_id"] as? String, "suica_test")
        XCTAssertEqual(json?["success"] as? Bool, true)
    }
}

final class NFCErrorTests: XCTestCase {
    
    func testErrorMessages() {
        // Given & When & Then
        XCTAssertEqual(NFCError.nfcNotAvailable.localizedDescription, ErrorMessage.NFC_NOT_AVAILABLE)
        XCTAssertEqual(NFCError.nfcDisabled.localizedDescription, ErrorMessage.NFC_DISABLED)
        XCTAssertEqual(NFCError.multipleCardsDetected.localizedDescription, ErrorMessage.MULTIPLE_CARDS_DETECTED)
        XCTAssertEqual(NFCError.readTimeout.localizedDescription, ErrorMessage.READ_TIMEOUT)
        XCTAssertEqual(NFCError.unsupportedCard.localizedDescription, ErrorMessage.UNSUPPORTED_CARD)
    }
    
    func testRetryableErrors() {
        // Given & When & Then
        XCTAssertTrue(NFCError.networkError(underlying: nil).isRetryable)
        XCTAssertTrue(NFCError.readTimeout.isRetryable)
        XCTAssertTrue(NFCError.apiError(statusCode: 500, message: nil).isRetryable)
        
        XCTAssertFalse(NFCError.nfcNotAvailable.isRetryable)
        XCTAssertFalse(NFCError.nfcDisabled.isRetryable)
        XCTAssertFalse(NFCError.multipleCardsDetected.isRetryable)
    }
}