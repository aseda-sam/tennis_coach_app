/** Serve window types. */

export type CourtSide = 'deuce' | 'ad';
export type ServeSubtype = 'flat' | 'slice' | 'kick';
export type InOut = 'in' | 'out_long' | 'out_wide' | 'net' | 'unknown';

export interface ServeWindow {
  id: number;
  video_id: number;
  player_id: number;
  start_timestamp: number;
  end_timestamp: number;
  contact_timestamp: number | null;
  source: string;
  status: string;
  confidence: number | null;
  model_version: string | null;
  court_side: CourtSide | null;
  serve_number: number | null;
  serve_subtype: ServeSubtype | null;
  in_out: InOut | null;
  created_at: string;
}

export interface ServeWindowCreate {
  video_id: number;
  player_id?: number | null;
  start_timestamp: number;
  end_timestamp: number;
  contact_timestamp?: number | null;
  court_side?: CourtSide | null;
  serve_number?: number | null;
  serve_subtype?: ServeSubtype | null;
  in_out?: InOut | null;
}

export interface ServeWindowUpdate {
  player_id?: number | null;
  start_timestamp?: number | null;
  end_timestamp?: number | null;
  contact_timestamp?: number | null;
  court_side?: CourtSide | null;
  serve_number?: number | null;
  serve_subtype?: ServeSubtype | null;
  in_out?: InOut | null;
}

export interface ServeWindowFilters {
  player_id?: number;
  court_side?: CourtSide;
  video_id?: number;
  start_date?: string;
  end_date?: string;
}
