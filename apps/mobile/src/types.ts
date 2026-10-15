export type Style = "cgi_3d";

/** Temas narrativos alinhados ao web (`apps/web/src/types.ts`). */
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
  | "alfabetizacao_inicial"
  | "pensamento_matematico"
  | "cores"
  | "opostos_espacial"
  | "higiene_desfralde"
  | "rotina_dormir"
  | "alimentacao_saudavel"
  | "vestir_autonomia"
  | "literacia_emocional"
  | "consciencia_corporal"
  | "compartilhar_revezar"
  | "animais_sons"
  | "transporte_ajudantes"
  | "clima_estacoes";

export type ThemeGroup = "aventura" | "datas" | "educativo";

export interface Project {
  id: string;
  status: string;
  style: string | null;
  theme?: string | null;
  extra_theme?: string | null;
  child_name?: string | null;
  child_age?: number | null;
  dedication?: string | null;
  story_text: string | null;
  ebook_url: string | null;
  video_url: string | null;
  narrated_video_url?: string | null;
  character_approved_at?: string | null;
  book_approved_at?: string | null;
  print_requested_at?: string | null;
  print_status?: string | null;
  created_at: string;
}

export type JobType =
  | "AVATAR"
  | "STORY"
  | "EBOOK"
  | "STORYBOARD"
  | "VIDEO"
  | "NARRATED_VIDEO"
  | "REALISTIC"
  | "EXTRA_CHARACTER";

export interface Job {
  id: string;
  project_id: string;
  type: JobType;
  status: "PENDING" | "RUNNING" | "DONE" | "FAILED";
  cost_credits: number;
  attempts: number;
  error: string | null;
}

export interface UploadUrl {
  asset_id: string;
  storage_key: string;
  upload_url: string;
  expires_in: number;
}

export interface ProjectAssets {
  character_url: string | null;
  realistic_url: string | null;
  extra_characters: { name: string; url: string }[];
  page_images: string[];
  ebook_url: string | null;
  video_url: string | null;
  narrated_video_url: string | null;
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

export type StudioStep = "avatar" | "story" | "ebook" | "video" | "narrated-video";
