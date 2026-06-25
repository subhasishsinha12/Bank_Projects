module.exports = {
  content: ["./src/**/*.{js,jsx}", "./index.html"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: '#050D1A', 2: '#0A1628', 3: '#0F1F38', 4: '#162848', 5: '#1E3560' },
        gold: { DEFAULT: '#C9A84C', bright: '#E8C96A', dim: '#7A6230' },
        electric: '#4FC3F7',
        mint: '#50E3C2',
        violet: '#A78BFA',
        crimson: '#FF5B5B',
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'monospace'],
        serif: ['"Cormorant Garamond"', 'serif'],
        sans: ['Inter', 'sans-serif'],
      }
    }
  },
  plugins: [require('@tailwindcss/forms')],
}
