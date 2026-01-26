/**
 * Validation utilities for the tennis coach application
 */

export interface TimestampValidationResult {
  isValid: boolean;
  error?: string;
}

/**
 * Validates a timestamp for ball contact creation/editing
 * @param timestamp - The timestamp in seconds
 * @param videoDuration - The total duration of the video in seconds
 * @returns Validation result with error message if invalid
 */
export function validateTimestamp(
  timestamp: number,
  videoDuration: number
): TimestampValidationResult {
  // Check if timestamp is a valid number
  if (isNaN(timestamp) || !isFinite(timestamp)) {
    return {
      isValid: false,
      error: 'Timestamp must be a valid number',
    };
  }

  // Check if timestamp is negative
  if (timestamp < 0) {
    return {
      isValid: false,
      error: 'Timestamp cannot be negative',
    };
  }

  // Check if timestamp exceeds video duration
  if (videoDuration > 0 && timestamp > videoDuration) {
    return {
      isValid: false,
      error: `Timestamp (${formatTime(timestamp)}) exceeds video duration (${formatTime(videoDuration)})`,
    };
  }

  // Check if timestamp is too close to the end (within 0.1 seconds)
  if (videoDuration > 0 && timestamp >= videoDuration - 0.1) {
    return {
      isValid: false,
      error: `Timestamp is too close to the end of the video`,
    };
  }

  return { isValid: true };
}

/**
 * Formats a timestamp in seconds to MM:SS format
 * @param seconds - Time in seconds
 * @returns Formatted time string
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Formats a timestamp in seconds to MM:SS.S format (with decimal)
 * @param seconds - Time in seconds
 * @returns Formatted time string with decimal precision
 */
export function formatTimeWithDecimal(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toFixed(1).padStart(4, '0')}`;
}

/**
 * Validates that a timestamp is within a reasonable range for manual input
 * @param timestamp - The timestamp in seconds
 * @param videoDuration - The total duration of the video in seconds
 * @returns Validation result with error message if invalid
 */
export function validateManualTimestamp(
  timestamp: number,
  videoDuration: number
): TimestampValidationResult {
  // Basic timestamp validation
  const basicValidation = validateTimestamp(timestamp, videoDuration);
  if (!basicValidation.isValid) {
    return basicValidation;
  }

  // No additional restrictions - serve attempts can start from the beginning of the video
  return { isValid: true };
}

/**
 * Validates an optional contact timestamp against a serve range.
 * @param contactTimestamp - The optional contact timestamp in seconds
 * @param startTimestamp - Serve attempt start timestamp in seconds
 * @param endTimestamp - Serve attempt end timestamp in seconds
 * @param videoDuration - The total duration of the video in seconds
 * @returns Validation result with error message if invalid
 */
export function validateContactTimestamp(
  contactTimestamp: number | null,
  startTimestamp: number,
  endTimestamp: number,
  videoDuration: number
): TimestampValidationResult {
  if (contactTimestamp === null) {
    return { isValid: true };
  }

  const basicValidation = validateTimestamp(contactTimestamp, videoDuration);
  if (!basicValidation.isValid) {
    return basicValidation;
  }

  if (contactTimestamp < startTimestamp || contactTimestamp > endTimestamp) {
    return {
      isValid: false,
      error: 'Contact timestamp must be between start and end time',
    };
  }

  return { isValid: true };
}
