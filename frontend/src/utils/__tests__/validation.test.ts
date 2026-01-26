import {
  validateContactTimestamp,
  formatTime,
  formatTimeWithDecimal,
  validateManualTimestamp,
  validateTimestamp,
} from '../validation';

describe('Validation Utils', () => {
  describe('validateTimestamp', () => {
    it('should validate a valid timestamp', () => {
      const result = validateTimestamp(30.5, 60);
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should reject negative timestamps', () => {
      const result = validateTimestamp(-5, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Timestamp cannot be negative');
    });

    it('should reject timestamps exceeding video duration', () => {
      const result = validateTimestamp(65, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe(
        'Timestamp (1:05) exceeds video duration (1:00)'
      );
    });

    it('should reject timestamps too close to the end', () => {
      const result = validateTimestamp(59.9, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe(
        'Timestamp is too close to the end of the video'
      );
    });

    it('should reject NaN timestamps', () => {
      const result = validateTimestamp(NaN, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Timestamp must be a valid number');
    });

    it('should reject infinite timestamps', () => {
      const result = validateTimestamp(Infinity, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Timestamp must be a valid number');
    });

    it('should handle zero duration gracefully', () => {
      const result = validateTimestamp(10, 0);
      expect(result.isValid).toBe(true);
    });
  });

  describe('validateManualTimestamp', () => {
    it('should validate a valid manual timestamp', () => {
      const result = validateManualTimestamp(30.5, 60);
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should allow timestamps from the beginning of the video', () => {
      const result = validateManualTimestamp(0, 60);
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should allow timestamps very early in the video', () => {
      const result = validateManualTimestamp(0.1, 60);
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should inherit basic validation from validateTimestamp', () => {
      const result = validateManualTimestamp(-5, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Timestamp cannot be negative');
    });
  });

  describe('validateContactTimestamp', () => {
    it('should allow null contact timestamp', () => {
      const result = validateContactTimestamp(null, 1, 2, 60);
      expect(result.isValid).toBe(true);
    });

    it('should allow contact timestamp within range', () => {
      const result = validateContactTimestamp(1.5, 1, 2, 60);
      expect(result.isValid).toBe(true);
    });

    it('should reject contact timestamp before start', () => {
      const result = validateContactTimestamp(0.5, 1, 2, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe(
        'Contact timestamp must be between start and end time'
      );
    });

    it('should reject contact timestamp after end', () => {
      const result = validateContactTimestamp(2.5, 1, 2, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe(
        'Contact timestamp must be between start and end time'
      );
    });

    it('should inherit basic timestamp validation', () => {
      const result = validateContactTimestamp(-1, 0, 2, 60);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Timestamp cannot be negative');
    });
  });

  describe('formatTime', () => {
    it('should format seconds correctly', () => {
      expect(formatTime(0)).toBe('0:00');
      expect(formatTime(30)).toBe('0:30');
      expect(formatTime(60)).toBe('1:00');
      expect(formatTime(90)).toBe('1:30');
      expect(formatTime(125)).toBe('2:05');
    });

    it('should handle decimal seconds by truncating', () => {
      expect(formatTime(30.7)).toBe('0:30');
      expect(formatTime(60.9)).toBe('1:00');
    });
  });

  describe('formatTimeWithDecimal', () => {
    it('should format seconds with decimal precision', () => {
      expect(formatTimeWithDecimal(0)).toBe('0:00.0');
      expect(formatTimeWithDecimal(30)).toBe('0:30.0');
      expect(formatTimeWithDecimal(30.5)).toBe('0:30.5');
      expect(formatTimeWithDecimal(60.7)).toBe('1:00.7');
      expect(formatTimeWithDecimal(125.3)).toBe('2:05.3');
    });
  });
});
