export interface AdminUser {
  user_id: number;
  first_name: string;
  username?: string;
  access_token: string;
}

export interface ErrorEntry {
  id: number;
  title_ru: string | null;
  title_uz: string | null;
  keywords_ru: string[] | null;
  keywords_uz: string[] | null;
  solution_ru: string | null;
  solution_uz: string | null;
  solution_video_file_id: string | null;
  solution_image_file_id: string | null;
  created_at: string;
}

export interface PaginatedErrors {
  items: ErrorEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface Group {
  chat_id: number;
  title: string | null;
  username: string | null;
  chat_type: string | null;
  added_by_id: number | null;
  added_by_name: string | null;
  added_by_username: string | null;
  status: "pending" | "approved" | "rejected";
  approved_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface OverviewStats {
  today_questions: number;
  total_groups: number;
  approved_groups: number;
  total_errors_in_db: number;
  resolution_rate_percent: number;
  avg_response_time_sec: number | null;
}

export interface DailyPoint {
  date: string;
  questions: number;
  resolved: number;
}

export interface TopError {
  error_id: number | null;
  title: string;
  count: number;
}

export interface GroupStat {
  chat_id: number;
  title: string | null;
  questions: number;
  resolved_by_ai: number;
  resolved_by_support: number;
}
