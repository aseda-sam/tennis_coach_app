/** Player profile types. */

export interface PlayerProfileUpdate {
  name?: string;
  dominant_hand?: string;
  backhand_style?: string | null;
  height_cm?: number | null;
  age_group?: string | null;
  gender?: string | null;
  notes?: string | null;
}

export interface PlayerInfo {
  id: number;
  name: string;
  dominant_hand: string;
  backhand_style?: string | null;
  height_cm?: number | null;
  age_group?: string | null;
  gender?: string | null;
  notes?: string | null;
  /** True when this player represents the account owner. */
  is_self?: boolean;
  created_at: string;
  updated_at?: string | null;
}
