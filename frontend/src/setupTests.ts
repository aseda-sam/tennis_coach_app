// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock ResizeObserver for jsdom
(globalThis as unknown as Record<string, unknown>).ResizeObserver =
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

// Node 25+ ships its own Web Storage API, which collides with jsdom's and
// leaves window.localStorage undefined under vitest
// (https://github.com/vitest-dev/vitest/issues/8757). Provide an in-memory
// Storage when the environment didn't. No-op on Node versions where jsdom's
// own storage works (e.g. Node 20 in CI).
class MemoryStorage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

for (const name of ['localStorage', 'sessionStorage'] as const) {
  if (typeof globalThis[name]?.clear !== 'function') {
    Object.defineProperty(globalThis, name, {
      value: new MemoryStorage(),
      configurable: true,
      writable: true,
    });
  }
}
