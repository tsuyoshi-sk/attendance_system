import Foundation

@MainActor
final class ReportService: ObservableObject {
    static let shared = ReportService()
    
    @Published private(set) var todayReport: DailyReport?
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    
    private init() {}
    
    func fetchTodayReport() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let todayString = formatter.string(from: Date())
        
        guard let url = URL(string: "\(API.BASE_URL)\(API.Endpoint.dailyReport)/\(todayString)") else {
            errorMessage = "無効なURLです"
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        do {
            let (data, response) = try await APIClient.shared.perform(request, requiresAuth: true)
            guard let httpResponse = response as? HTTPURLResponse,
                  200..<300 ~= httpResponse.statusCode else {
                throw NFCError.apiError(statusCode: (response as? HTTPURLResponse)?.statusCode ?? -1, message: nil)
            }
            
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            todayReport = try decoder.decode(DailyReport.self, from: data)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct DailyReport: Decodable {
    let date: String
    let status: String
    let punchRecords: [PunchRecord]
    
    enum CodingKeys: String, CodingKey {
        case date
        case status
        case punchRecords = "punch_records"
    }
}

struct PunchRecord: Decodable, Identifiable {
    let id = UUID()
    let punchType: String
    let timestamp: Date
    
    enum CodingKeys: String, CodingKey {
        case punchType = "punch_type"
        case timestamp
    }
}
