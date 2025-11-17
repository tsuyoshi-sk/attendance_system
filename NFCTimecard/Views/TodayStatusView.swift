import SwiftUI

struct TodayStatusView: View {
    @StateObject private var reportService = ReportService.shared
    
    var body: some View {
        NavigationView {
            Group {
                if reportService.isLoading {
                    ProgressView("読み込み中...")
                } else if let report = reportService.todayReport {
                    List {
                        Section(header: Text("現在の状態")) {
                            Text(report.status.isEmpty ? "不明" : report.status)
                                .font(.headline)
                        }
                        
                        Section(header: Text("本日の打刻履歴")) {
                            if report.punchRecords.isEmpty {
                                Text("打刻履歴がありません")
                                    .foregroundColor(.secondary)
                            } else {
                                ForEach(report.punchRecords) { record in
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(record.punchTypeLabel)
                                            .font(.headline)
                                        Text(record.timestamp.formatted(date: .omitted, time: .shortened))
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
                        }
                    }
                    .listStyle(InsetGroupedListStyle())
                } else if let message = reportService.errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 48))
                            .foregroundColor(.orange)
                        Text("読み込みに失敗しました")
                            .font(.headline)
                        Text(message)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding()
                } else {
                    Text("データがありません")
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("今日のステータス")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: {
                        Task { await reportService.fetchTodayReport() }
                    }) {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
            .task {
                await reportService.fetchTodayReport()
            }
        }
    }
}

private extension PunchRecord {
    var punchTypeLabel: String {
        switch punchType {
        case "in": return "出勤"
        case "out": return "退勤"
        case "outside": return "外出"
        case "return": return "戻り"
        default: return punchType
        }
    }
}
