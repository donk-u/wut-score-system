import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite' // 👈 引入全新引擎

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(), // 👈 挂载引擎
  ],
})