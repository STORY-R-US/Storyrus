export type Style = "cgi_3d" | "realistic" | "cartoon" | "anime";

export type Theme =
  | "adventure"
  | "princess"
  | "superhero"
  | "space"
  | "underwater"
  | "dinosaurs"
  | "fantasy"
  | "birthday"
  | "christmas"
  | "easter"
  | "childrens_day"
  | "mothers_day"
  | "fathers_day"
  | "new_year"
  // Temas educativos (Linguagem & Conceitos Fundamentais)
  | "alfabetizacao_inicial"
  | "pensamento_matematico"
  | "cores"
  | "opostos_espacial"
  // Temas educativos (Habilidades de Vida & Rotinas Diárias)
  | "higiene_desfralde"
  | "rotina_dormir"
  | "alimentacao_saudavel"
  | "vestir_autonomia"
  // Temas educativos (Autoconsciência & Aprendizagem Socioemocional)
  | "literacia_emocional"
  | "consciencia_corporal"
  | "compartilhar_revezar"
  // Temas educativos (Descoberta & Exploração do Mundo)
  | "animais_sons"
  | "transporte_ajudantes"
  | "clima_estacoes"
  | "biblico"
  | "casamento"
  | "recem_nascidos";

// História pronta do catálogo (template traduzido, personalizado com o nome).
export interface StoryTemplate {
  id: string;
  titulo: string;
  genero: string;
  idade: string;
  tematica: string;
  emoji: string;
  paginas: number;
}

export interface ExtraCharacter {
  name: string;
  storage_key: string;
  mime: string;
  character_storage_key?: string;
  character_mime?: string;
}

export interface Project {
  processing_revoked_at?: string | null;
  book_profile?: {
    version: number;
    stage: string;
    title: string;
    gender: string;
    languages: string[];
    current_page: number;
    costume?: string;
    palette?: string;
    trait?: string;
    interest?: string;
    locales?: Record<string, { title: string; left: string; right: string }>;
    stories?: Record<string, string>;
    credits_fallback?: boolean;
  } | null;
  id: string;
  status: string;
  style: string | null;
  theme?: string | null;
  extra_theme?: string | null;
  child_name?: string | null;
  child_age?: number | null;
  dedication?: string | null;
  language?: string | null;
  extra_characters?: ExtraCharacter[];
  story_text: string | null;
  ebook_url: string | null;
  video_url: string | null;
  narrated_video_url?: string | null;
  character_approved_at?: string | null;
  book_approved_at?: string | null;
  book_size?: "M" | "P" | null;
  cover_type?: "soft" | "hard" | null;
  purchase_flow?: {
    title?: string | null;
    theme_description?: string | null;
    photo_notes?: string;
    stage?: string;
    preview_ready_at?: string | null;
    preview_approved_at?: string | null;
    full_book_ready_at?: string | null;
    quoted_at?: string | null;
  } | null;
  print_requested_at?: string | null;
  print_status?: string | null;
  created_at: string;
}

export interface JobProgress {
  stage?: string;
  done?: number;
  total?: number;
}

export interface Job {
  id: string;
  project_id: string;
  type: "AVATAR" | "STORY" | "EBOOK" | "STORYBOARD" | "VIDEO" | "NARRATED_VIDEO" | "REALISTIC" | "EXTRA_CHARACTER";
  status: "PENDING" | "RUNNING" | "DONE" | "FAILED";
  provider: string | null;
  cost_credits: number;
  cost_usd?: number | null;
  attempts: number;
  error: string | null;
  created_at: string;
  result?: {
    progress?: JobProgress;
    payload?: { preview_chain?: boolean; purchase_full_book?: boolean; brief?: string; duration_s?: number };
  } | null;
}

export interface JobAccepted {
  job_id: string;
  status: string;
  type: Job["type"];
  estimated_cost_credits: number;
}

export interface UsageBucket {
  key: string;
  usd: number;
  jobs: number;
}

export interface UsageBook {
  project_id: string;
  child_name: string | null;
  status: string;
  usd: number | null;
  unmeasured_jobs: number;
  updated_at: string;
}

export interface UsageJob {
  id: string;
  project_id: string;
  child_name: string | null;
  type: string;
  status: string;
  provider: string | null;
  cost_usd: number | null;
  attempts: number;
  created_at: string;
}

export interface UsageEvent {
  id: string | null;
  job_id: string | null;
  project_id: string;
  child_name: string | null;
  kind: string;
  provider: string;
  action: string;
  label: string;
  cost_usd: number | null;
  created_at: string;
}

export interface OrderBookFile {
  label: string;
  url: string;
  kind?: string | null;
  provider?: string | null;
}

export interface OrderTicket {
  id: string;
  project_id: string;
  summary: string;
  created_at: string;
  child_age?: number | null;
  book_size?: string | null;
  cover_type?: string | null;
  style?: string | null;
  photo_urls?: string[];
  has_story?: boolean;
  book_files?: OrderBookFile[];
  generation_status?: "queued" | "generating" | "ready" | "partial" | "failed" | "demo";
  generation_stage?: string | null;
  generated_images?: number;
  image_provider?: string | null;
  image_model?: string | null;
  generation_error?: string | null;
  credits_fallback?: boolean;
  print_order_id?: string | null;
  print_code?: string | null;
  print_status?: string | null;
  block_reason?: string | null;
  tracking_code?: string | null;
  payment_status?: string | null;
  amount_cents?: number | null;
  account_email?: string | null;
  mine?: boolean;
  child_name?: string | null;
  dedication?: string | null;
  quantity?: number | null;
  recipient_name?: string | null;
  postal_code?: string | null;
  street?: string | null;
  number?: string | null;
  complement?: string | null;
  district?: string | null;
  city?: string | null;
  state?: string | null;
}

export interface FreightOption {
  service_id: number;
  service_name: string;
  price_cents: number;
  delivery_days: number | null;
}

export interface PrintAddress {
  recipient_name: string;
  postal_code: string;
  street: string;
  number: string;
  complement?: string;
  district: string;
  city: string;
  state: string;
}

export interface PrintOrder {
  id: string;
  project_id: string;
  code: string;
  book_size: string | null;
  cover_type: string | null;
  quantity: number;
  status: string;
  block_reason: string | null;
  book_price_cents: number | null;
  freight_options: FreightOption[];
  freight_service_id: number | null;
  freight_service_name: string | null;
  freight_price_cents: number | null;
  freight_days: number | null;
  payment_status: string;
  amount_cents: number | null;
  tracking_code: string | null;
  label_error: string | null;
  checkout_available: boolean;
  checkout_url: string | null;
  recipient_name: string | null;
  postal_code: string | null;
  street: string | null;
  number: string | null;
  complement: string | null;
  district: string | null;
  city: string | null;
  state: string | null;
}

export interface UsageAnomaly {
  kind: string;
  severity: string;
  message: string;
}

export interface OwnerUser {
  id: string;
  email: string;
  credits: number;
  created_at: string;
  project_count: number;
  full_name?: string | null;
  phone?: string | null;
  email_verified?: boolean;
  postal_code?: string | null;
  street?: string | null;
  number?: string | null;
  complement?: string | null;
  district?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  terms_accepted_at?: string | null;
  is_admin?: boolean;
  adult_confirmed?: boolean;
}

export interface OwnerUserUpdate {
  email?: string;
  credits?: number;
  email_verified?: boolean;
  full_name?: string | null;
  phone?: string | null;
  postal_code?: string | null;
  street?: string | null;
  number?: string | null;
  complement?: string | null;
  district?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  password?: string;
  is_admin?: boolean;
  adult_confirmed?: boolean;
}

export interface OwnerUsersReport {
  total: number;
  users: OwnerUser[];
}

export interface UsageReport {
  timezone: string;
  from_at: string;
  to_at: string;
  today_usd: number;
  month_usd: number;
  range_usd: number;
  books_count: number;
  avg_book_usd: number | null;
  by_type: UsageBucket[];
  by_provider: UsageBucket[];
  books: UsageBook[];
  recent_jobs: UsageJob[];
  events?: UsageEvent[];
  events_count?: number;
  daily_spend_usd_ceiling?: number | null;
  daily_credits_ceiling?: number | null;
  today_credits?: number;
  reserved_usd?: number;
  anomalies?: UsageAnomaly[];
  orders?: OrderTicket[];
  users_total?: number;
  projects_total?: number;
  projects_awaiting_photo?: number;
  error_report?: ErrorReportItem[];
}

export interface ErrorReportItem {
  created_at: string;
  project_id?: string | null;
  child_name?: string | null;
  stage: string;
  message: string;
}

export interface UploadUrl {
  asset_id: string;
  storage_key: string;
  upload_url: string;
  expires_in: number;
}

export interface UserVoice {
  id: string;
  name: string;
  is_default: boolean;
  mime_type: string;
  created_at: string;
}

export interface VoiceList {
  items: UserVoice[];
  custom_voice_available: boolean;
}
