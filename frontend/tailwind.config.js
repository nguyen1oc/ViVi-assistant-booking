/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  // Preserve the completed testing branch as the visual baseline while legacy
  // selectors are migrated incrementally to Tailwind utility classes.
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: { ink: '#171a20', paper: '#f4f4f4', brand: '#1464f4' },
      fontFamily: {
        sans: ['Be Vietnam Pro', 'Outfit Variable', 'ui-sans-serif', 'system-ui'],
      },
    },
  },
  plugins: [],
}
