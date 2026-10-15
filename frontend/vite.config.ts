import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  envDir: '..', // lit VITE_API_URL dans le .env à la racine du projet (ou dans l'environnement)
});
