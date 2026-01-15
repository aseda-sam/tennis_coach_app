import {
  STROKE_SUBTYPES_BY_TYPE,
  STROKE_SUBTYPE_LABELS,
  STROKE_TYPE_LABELS,
  getSubtypesForType,
  isValidSubtypeForType,
  type StrokeType,
} from '../shotTypes';

describe('shotTypes', () => {
  describe('STROKE_TYPE_LABELS', () => {
    it('should have labels for all stroke types', () => {
      const strokeTypes: StrokeType[] = [
        'ground_stroke',
        'serve',
        'return',
        'volley',
        'overhead',
      ];

      strokeTypes.forEach((type) => {
        expect(STROKE_TYPE_LABELS[type]).toBeDefined();
        expect(typeof STROKE_TYPE_LABELS[type]).toBe('string');
      });
    });
  });

  describe('STROKE_SUBTYPES_BY_TYPE', () => {
    it('should have subtypes for all stroke types', () => {
      const strokeTypes: StrokeType[] = [
        'ground_stroke',
        'serve',
        'return',
        'volley',
        'overhead',
      ];

      strokeTypes.forEach((type) => {
        expect(STROKE_SUBTYPES_BY_TYPE[type]).toBeDefined();
        expect(Array.isArray(STROKE_SUBTYPES_BY_TYPE[type])).toBe(true);
        expect(STROKE_SUBTYPES_BY_TYPE[type].length).toBeGreaterThan(0);
      });
    });

    it('should have correct subtypes for ground_stroke', () => {
      const subtypes = STROKE_SUBTYPES_BY_TYPE.ground_stroke;
      expect(subtypes).toContain('forehand_flat');
      expect(subtypes).toContain('forehand_topspin');
      expect(subtypes).toContain('backhand_flat');
      expect(subtypes).toContain('drop_shot');
    });

    it('should have correct subtypes for serve', () => {
      const subtypes = STROKE_SUBTYPES_BY_TYPE.serve;
      expect(subtypes).toContain('flat');
      expect(subtypes).toContain('topspin_kick');
      expect(subtypes).toContain('slice');
      expect(subtypes).toContain('underarm');
    });
  });

  describe('getSubtypesForType', () => {
    it('should return subtypes for valid stroke type', () => {
      const subtypes = getSubtypesForType('ground_stroke');
      expect(Array.isArray(subtypes)).toBe(true);
      expect(subtypes.length).toBeGreaterThan(0);
    });

    it('should return empty array for null/undefined', () => {
      expect(getSubtypesForType(null)).toEqual([]);
      expect(getSubtypesForType(undefined)).toEqual([]);
    });
  });

  describe('isValidSubtypeForType', () => {
    it('should return true for valid subtype', () => {
      expect(
        isValidSubtypeForType('ground_stroke', 'forehand_topspin')
      ).toBe(true);
      expect(isValidSubtypeForType('serve', 'flat')).toBe(true);
    });

    it('should return false for invalid subtype', () => {
      expect(isValidSubtypeForType('ground_stroke', 'smash')).toBe(false);
      expect(isValidSubtypeForType('serve', 'forehand_flat')).toBe(false);
    });

    it('should return true for empty/null subtype (optional)', () => {
      expect(isValidSubtypeForType('ground_stroke', null)).toBe(true);
      expect(isValidSubtypeForType('ground_stroke', '')).toBe(true);
      expect(isValidSubtypeForType('ground_stroke', undefined)).toBe(true);
    });

    it('should return false when stroke type is null/undefined', () => {
      expect(isValidSubtypeForType(null, 'forehand_topspin')).toBe(false);
      expect(isValidSubtypeForType(undefined, 'forehand_topspin')).toBe(false);
    });
  });

  describe('STROKE_SUBTYPE_LABELS', () => {
    it('should have labels for common subtypes', () => {
      expect(STROKE_SUBTYPE_LABELS['forehand_topspin']).toBeDefined();
      expect(STROKE_SUBTYPE_LABELS['backhand_flat']).toBeDefined();
      expect(STROKE_SUBTYPE_LABELS['smash']).toBeDefined();
    });
  });
});
