import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        surface: '#f5f7fb',
        ink: '#172033',
        muted: '#667085',
        primary: '#2563eb'
      },
      boxShadow: {
        card: '0 16px 38px rgba(15, 23, 42, 0.06)'
      }
    }
  },
  plugins: []
} satisfies Config
