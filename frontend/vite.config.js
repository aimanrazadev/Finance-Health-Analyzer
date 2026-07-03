import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import locator from '@locator/babel-jsx'

export default defineConfig(({ mode }) => ({
  plugins: [
    react({
      babel: {
        plugins: mode === 'development' ? [locator] : [],
      },
    }),
  ],
  build: {
    // Vite 8's production minifier currently corrupts Recharts' CommonJS
    // wrappers (for example, emitting `var t = t()` in the PieChart chunk).
    minify: false,
    rolldownOptions: {
      output: {
        // Keep Recharts and its CommonJS helpers together. Splitting them
        // currently creates circular helper imports in Rolldown production builds.
        codeSplitting: false,
      },
    },
  },
}))
