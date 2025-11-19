import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getEmployees, EmployeeSummary } from "../lib/api";

export function EmployeesPage() {
  const [query, setQuery] = useState("");
  const [employees, setEmployees] = useState<EmployeeSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      setIsLoading(true);
      try {
        const data = await getEmployees(query);
        setEmployees(data);
      } catch (error) {
        console.error("Failed to fetch employees:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [query]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold text-slate-800 mb-2">従業員一覧</h1>

      <div className="flex gap-2 mb-4">
        <input
          className="flex-1 rounded-lg border px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          placeholder="名前・社員番号で検索"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {isLoading ? (
        <div className="text-gray-500 text-sm py-8 text-center">読み込み中...</div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
            <table className="w-full text-sm">
            <thead className="bg-gray-50">
                <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">社員番号</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">氏名</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">所属</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">ステータス</th>
                </tr>
            </thead>
            <tbody>
                {employees.map((emp) => (
                <tr
                    key={emp.id}
                    className="border-t hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/employees/${emp.id}`)}
                >
                    <td className="px-4 py-3 text-gray-700">{emp.employeeCode}</td>
                    <td className="px-4 py-3 font-medium text-slate-800">{emp.name}</td>
                    <td className="px-4 py-3 text-gray-700">{emp.departmentName}</td>
                    <td className="px-4 py-3">
                    <span
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        emp.status === "勤務中"
                            ? "bg-green-100 text-green-800"
                            : emp.status === "休憩中"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                    >
                        {emp.status}
                    </span>
                    </td>
                </tr>
                ))}
            </tbody>
            </table>
        </div>
      )}
      { !isLoading && employees.length === 0 && (
          <div className="text-center py-12 text-gray-500">
              <p>該当する従業員が見つかりませんでした。</p>
          </div>
      )}
    </div>
  );
}