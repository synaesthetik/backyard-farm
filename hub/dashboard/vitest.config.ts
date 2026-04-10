import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export default defineConfig({
  plugins: [svelte({ hot: false })],
  resolve: {
    conditions: ['browser'],
    alias: {
      // SvelteKit path aliases for test environment
      $lib: path.resolve('./src/lib'),
      '$app/navigation': path.resolve('./src/__mocks__/navigation.ts'),
      '$app/stores': path.resolve('./src/__mocks__/stores.ts'),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
  },
});
