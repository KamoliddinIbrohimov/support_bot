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
  bot_mode: "learning" | "knowledge" | "express";
  poster_auto_answer: boolean;
  approved_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface GroupUserRole {
  id: number;
  group_id: number;
  telegram_user_id: number;
  username: string | null;
  full_name: string | null;
  role: "poster_staff" | "plugin_staff" | "customer";
  confidence_score: number;
  is_manual_override: boolean;
  updated_at: string;
}

export interface LearningFeedEntry {
  id: number;
  group_id: number;
  question_text: string | null;
  answer_text: string | null;
  question_user_id: number | null;
  answer_user_id: number | null;
  question_username: string | null;
  answer_username: string | null;
  is_confirmed: boolean;
  created_at: string;
}

export interface GroupDetailStats {
  chat_id: number;
  title: string | null;
  status: string;
  bot_mode: string;
  poster_auto_answer: boolean;
  total_questions: number;
  resolved_by_ai: number;
  resolved_by_support: number;
  unresolved: number;
  resolution_rate: number;
  top_errors: { error_id: number | null; title: string; count: number }[];
  timeline: { date: string; questions: number }[];
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
