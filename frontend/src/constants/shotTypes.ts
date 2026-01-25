/** Canonical shot type and subtype definitions for tennis strokes. */

export type StrokeType =
  | 'ground_stroke'
  | 'serve'
  | 'return'
  | 'volley'
  | 'overhead';

export const STROKE_SUBTYPES_BY_TYPE: Record<StrokeType, string[]> = {
  ground_stroke: [
    'forehand_flat',
    'forehand_topspin',
    'forehand_slice',
    'backhand_flat',
    'backhand_topspin',
    'backhand_slice',
    'drop_shot',
    'lob',
  ],
  serve: ['flat', 'topspin_kick', 'slice', 'underarm'],
  return: ['forehand', 'backhand'],
  volley: ['forehand', 'backhand', 'drop', 'half'],
  overhead: ['smash'],
};

export const STROKE_TYPE_LABELS: Record<StrokeType, string> = {
  ground_stroke: 'Ground Stroke',
  serve: 'Serve',
  return: 'Return',
  volley: 'Volley',
  overhead: 'Overhead',
};

export const STROKE_SUBTYPE_LABELS: Record<string, string> = {
  // Groundstrokes
  forehand_flat: 'Forehand Flat',
  forehand_topspin: 'Forehand Topspin',
  forehand_slice: 'Forehand Slice',
  backhand_flat: 'Backhand Flat',
  backhand_topspin: 'Backhand Topspin',
  backhand_slice: 'Backhand Slice',
  drop_shot: 'Drop Shot',
  lob: 'Lob',
  // Serves
  flat: 'Flat',
  topspin_kick: 'Topspin/Kick',
  slice: 'Slice',
  underarm: 'Underarm',
  // Returns
  forehand: 'Forehand',
  backhand: 'Backhand',
  // Volleys
  drop: 'Drop',
  half: 'Half Volley',
  // Overhead
  smash: 'Smash',
};

export function getSubtypesForType(
  strokeType: StrokeType | null | undefined
): string[] {
  if (!strokeType) {
    return [];
  }
  return STROKE_SUBTYPES_BY_TYPE[strokeType] || [];
}

export function isValidSubtypeForType(
  strokeType: StrokeType | null | undefined,
  strokeSubtype: string | null | undefined
): boolean {
  if (!strokeSubtype || strokeSubtype === '') {
    return true; // Subtype is optional
  }
  if (!strokeType) {
    return false;
  }
  return getSubtypesForType(strokeType).includes(strokeSubtype);
}
