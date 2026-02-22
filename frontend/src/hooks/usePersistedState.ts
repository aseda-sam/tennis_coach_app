import { useCallback, useState } from 'react';

function usePersistedState<T>(
  key: string,
  defaultValue: T
): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored !== null ? (JSON.parse(stored) as T) : defaultValue;
    } catch {
      return defaultValue;
    }
  });

  const setPersisted = useCallback(
    (v: T) => {
      setValue(v);
      try {
        localStorage.setItem(key, JSON.stringify(v));
      } catch {
        // localStorage full or unavailable — state still updates in memory
      }
    },
    [key]
  );

  return [value, setPersisted];
}

export default usePersistedState;
