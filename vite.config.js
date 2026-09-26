import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server pinned to 5180: 5173 (Vite's default) collides with other local
// Vite apps. strictPort fails loudly instead of silently picking another port.
export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5180, strictPort: true },
});
