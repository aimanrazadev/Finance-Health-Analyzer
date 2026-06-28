import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import locator from '@locator/babel-jsx'

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [locator],
      },
    }),
    tailwindcss(),
  ],
})