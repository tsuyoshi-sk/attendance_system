import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Legend } from "recharts";
import { getDashboardSummary } from "../lib/api"; // Make sure this path is correct

// Type definition from user prompt
type DashboardSummary = {
  totalEmployees: number;
  workingCount: number;
  onBreakCount: number;
  offCount: number;
  alerts: { id: string; type: string; message: string; severity: "high" | "medium" | "low" }[];
  lateCount: number;
  earlyLeaveCount: number;
  absenceSuspiciousCount: number;
  overtimeByDept: { deptName: string; overtimeHours: number }[];
};

const PIE_COLORS = ['#0088FE', '#00C49F', '#FFBB28'];
const ALERT_COLORS = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const res = await getDashboardSummary();
        setData(res);
      } catch(error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return <div className="p-6 text-gray-500">読み込み中...</div>;
  }
  
  if (!data) {
    return <div className="p-6 text-red-500">データの読み込みに失敗しました。</div>;
  }

  const statusChartData = [
    { name: "勤務中", value: data.workingCount },
    { name: "休憩中", value: data.onBreakCount },
    { name: "退勤済", value: data.offCount },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* タイトル */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-800">ダッシュボード</h1>
        <span className="text-sm text-gray-500">
          今日：{new Date().toLocaleDateString("ja-JP", { year: 'numeric', month: 'long', day: 'numeric' })}
        </span>
      </div>

      {/* 上段カード */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="md:col-span-2 bg-white rounded-xl shadow p-5">
          <p className="text-sm font-medium text-gray-500">現在の出勤状況</p>
          <div className="mt-2 flex items-end gap-2">
            <p className="text-4xl font-bold text-slate-800">{data.workingCount}</p>
            <p className="text-base text-gray-500 mb-1">
              / {data.totalEmployees} 人
            </p>
          </div>
        </div>

        <SummaryCard label="遅刻" value={data.lateCount} color="text-red-600" />
        <SummaryCard label="早退" value={data.earlyLeaveCount} color="text-yellow-600" />
        <SummaryCard label="欠勤疑い" value={data.absenceSuspiciousCount} color="text-orange-600" />
      </div>

      {/* 中段：グラフ */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* 勤務状態ドーナツ */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow p-4">
          <h2 className="text-base font-semibold mb-4 text-slate-700">勤務ステータス内訳</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={statusChartData}
                  innerRadius="60%"
                  outerRadius="85%"
                  paddingAngle={4}
                  dataKey="value"
                  cornerRadius={8}
                >
                  {statusChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${value}人`} />
                <Legend iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 残業ランキング */}
        <div className="lg:col-span-3 bg-white rounded-xl shadow p-4">
          <h2 className="text-base font-semibold mb-4 text-slate-700">部門別 残業時間ランキング (今月)</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={data.overtimeByDept} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                <XAxis dataKey="deptName" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip cursor={{fill: 'rgba(241, 245, 249, 0.5)'}} formatter={(value) => `${value}h`} />
                <Bar dataKey="overtimeHours" fill="#475569" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 下段：アラート */}
      <div className="bg-white rounded-xl shadow p-4">
        <h2 className="text-base font-semibold mb-4 text-slate-700">勤怠アラート</h2>
        {data.alerts.length === 0 ? (
          <div className="text-sm text-gray-500 text-center py-8">現在、特にアラートはありません。</div>
        ) : (
          <ul className="space-y-2">
            {data.alerts.map((a) => (
              <li
                key={a.id}
                className="flex items-center justify-between border rounded-lg px-4 py-3 text-sm hover:bg-gray-50"
              >
                <div className="font-medium text-slate-700">{a.message}</div>
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full ${ALERT_COLORS[a.severity]}`}
                >
                  {a.severity === "high" ? "重要" : a.severity === "medium" ? "注意" : "情報"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-white rounded-xl shadow p-5 flex flex-col justify-between">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <div className="mt-2 text-right">
        <span className={`text-3xl font-bold ${color}`}>{value}</span>
        <span className={`text-sm ml-1 ${color.replace('600', '500')}`}>人</span>
      </div>
    </div>
  );
}