/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Only needed when the dev server sits behind a proxy on a non-localhost host
// (e.g. a container preview). Leave it unset for normal local development:
//   VITE_DEV_ALLOWED_HOSTS="*" npm run dev
const allowedHosts = process.env.VITE_DEV_ALLOWED_HOSTS;

export default defineConfig({
  plugins: [react()],
  server: {
    // Bind to all interfaces so the dev server is reachable from a container
    // or a proxied preview URL, not just localhost.
    host: true,
    port: 5173,
    strictPort: false,
    ...(allowedHosts
      ? { allowedHosts: allowedHosts === "*" ? true : allowedHosts.split(",") }
      : {}),
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    css: false,
    restoreMocks: true,
    // Pin the API base URL so a developer's .env.local cannot change what the
    // client tests assert.
    env: {
      VITE_API_URL: "",
    },
  },
});
