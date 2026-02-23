/**
 * Extract a human-readable error message from an unknown API error.
 *
 * FastAPI returns validation errors as `{ detail: string }` in the response
 * body. The axios interceptor in api.ts normalises multi-field validation
 * errors to a single string, so `detail` is always a string by the time it
 * reaches callers.
 */
export function getApiErrorMessage(
  err: unknown,
  fallback = 'An error occurred'
): string {
  const error = err as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return error?.response?.data?.detail || error?.message || fallback;
}
