export type View = "front" | "back";
export type GenerationStatus = "not_generated" | "processing" | "ready" | "failed";
export interface UserSettings {
  display_name:string;
  body_front_url:string|null;
  body_back_url:string|null;
  body_front_cutout_url:string|null;
  body_back_cutout_url:string|null;
  body_reference_version:number;
  is_complete:boolean;
}
export interface Garment {
  id:string; name:string; brand:string|null; category:string; color:string|null;
  raw_front_url:string; raw_back_url:string|null; clean_front_url:string|null; clean_back_url:string|null;
  tryon_front_url:string|null; tryon_back_url:string|null; front_status:GenerationStatus; back_status:GenerationStatus;
  tryon_front_cutout_url:string|null; tryon_back_cutout_url:string|null;
  front_progress:number; back_progress:number;
  front_progress_stage:string|null; back_progress_stage:string|null;
  front_error:string|null; back_error:string|null; garment_version:number; created_at:string; updated_at:string;
}
export interface ServiceStatus { mode:string; available:boolean; device:string|null; detail:string; }
export interface Health { status:string; app:string; background_removal:ServiceStatus; virtual_try_on:ServiceStatus; }
