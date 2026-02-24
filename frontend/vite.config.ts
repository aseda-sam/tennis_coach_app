import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  base: '/tennis_coach_app/',
  plugins: [react()],
  server: {
    proxy: {
      '/v0': 'http://backend:8000',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['src/setupTests.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      thresholds: {
        branches: 5,
        functions: 5,
        lines: 12,
        statements: 12,
      },
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/index.tsx',
        'src/setupTests.ts',
      ],
    },
  },
});
