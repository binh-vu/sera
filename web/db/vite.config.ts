import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import dts from "vite-plugin-dts";

const __dirname = dirname(fileURLToPath(import.meta.url));

// https://vite.dev/config/
export default defineConfig({
  plugins: [dts({ tsconfigPath: "./tsconfig.json" })],
  build: {
    lib: {
      entry: resolve(__dirname, "src/index.ts"),
      name: "sera-db",
      // the proper extensions will be added
      fileName: "index",
    },
    rollupOptions: {
      // make sure to externalize deps that shouldn't be bundled
      // into your library
      external: ["mobx", "axios", "memoize-one", "validator"],
      output: {
        // Provide global variables to use in the UMD build
        // for externalized deps
        globals: {
          mobx: "mobx",
          axios: "axios",
          "memoize-one": "memoizeOne",
          validator: "validator",
        },
      },
    },
  },
});
