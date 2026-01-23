/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        surface: 'var(--surface)',
        'surface-light': 'var(--surface-light)',
        primary: 'var(--primary)',
        accent: 'var(--accent)',
        blue: 'var(--blue)',
        'blue-light': 'var(--blue-light)',
        'blue-dark': 'var(--blue-dark)',
        'blue-metallic': 'var(--blue-metallic)',
        'blue-metallic-light': 'var(--blue-metallic-light)',
        'blue-metallic-dark': 'var(--blue-metallic-dark)',
        'blue-navy': 'var(--blue-navy)',
        'blue-navy-light': 'var(--blue-navy-light)',
        'blue-navy-dark': 'var(--blue-navy-dark)',
        'blue-cobalt': 'var(--blue-cobalt)',
        'blue-cobalt-light': 'var(--blue-cobalt-light)',
        'blue-cobalt-dark': 'var(--blue-cobalt-dark)',
        success: 'var(--success)',
        warning: 'var(--warning)',
        error: 'var(--error)',
      },
      fontFamily: {
        inter: ['var(--font-inter)', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'sans-serif'],
        quando: ['var(--font-quando)', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
