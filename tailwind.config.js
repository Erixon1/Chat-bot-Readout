/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app.py",
    "./core/**/*.py",
    "./tools/**/*.py",
    "./static/**/*.html",
  ],
  darkMode: 'media',
  theme: {
    extend: {
      // Espejo de las variables --rd-* definidas en src/styles/input.css
      colors: {
        ink: {
          950: '#0A0A0B',
          900: '#141416',
          850: '#1B1B1E',
          700: '#26262B',
          600: '#34343A',
        },
        electric: {
          400: '#5A7DFF',
          500: '#2E5BFF',
        },
        paper: '#ECECEE',
      },
      fontFamily: {
        sans: ['"Archivo"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      }
    },
  },
  plugins: [],
}
