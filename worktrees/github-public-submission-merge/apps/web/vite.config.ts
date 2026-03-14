import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig( {
  plugins: [ react() ],
  optimizeDeps: {
    include: [ "@world-os/sdk", "@world-os/kernel" ]
  },
  build: {
    commonjsOptions: {
      include: [ /@world-os\/sdk/, /@world-os\/kernel/, /node_modules/ ]
    }
  },
  server: {
    port: 5173,
    host: true
  },
  define: {
    __API_URL__: JSON.stringify( process.env.VITE_API_URL || "http://localhost:3001" )
  }
} );
