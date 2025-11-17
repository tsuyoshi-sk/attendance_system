// ユーザー関連
export interface User {
  id: number;
  employee_id: string;
  name: string;
  email: string;
  department?: string;
  position?: string;
  is_admin: boolean;
  created_at: string;
}

// 打刻関連
export type PunchType = 'in' | 'out' | 'outside' | 'return';

export interface PunchRecord {
  id: number;
  employee_id: number;
  card_idm: string;
  punch_type: PunchType;
  timestamp: string;
  location?: string;
  note?: string;
  created_at: string;
}

export interface PunchRequest {
  card_idm: string;
  punch_type: PunchType;
  note?: string;
}

// ステータス
export type AttendanceStatus = 'working' | 'break' | 'outside' | 'off';

export interface TodayStatus {
  status: AttendanceStatus;
  punch_in_time?: string;
  punch_out_time?: string;
  break_start_time?: string;
  working_hours?: number;
  records: PunchRecord[];
}

// レポート関連
export interface DailyReport {
  date: string;
  status: AttendanceStatus;
  punch_in_time?: string;
  punch_out_time?: string;
  working_hours: number;
  break_time: number;
  overtime: number;
  punch_records: PunchRecord[];
  summary?: {
    total_hours: number;
    regular_hours: number;
    overtime_hours: number;
  };
}

export interface MonthlyReport {
  year_month: string;
  total_days: number;
  work_days: number;
  total_hours: number;
  total_overtime: number;
  daily_reports: DailyReport[];
  summary: {
    present_days: number;
    absent_days: number;
    late_days: number;
    early_leave_days: number;
    total_working_hours: number;
    average_working_hours: number;
  };
}

// 認証関連
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ページネーション
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// エラーレスポンス
export interface ApiError {
  detail: string;
  status_code?: number;
}
