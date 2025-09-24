import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import dts from "vite-plugin-dts";

const __dirname = dirname(fileURLToPath(import.meta.url));
console.log(__dirname)

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const localLibraryAlias = (() => {
    if (mode !== 'development') {
      return {}
    }
    // In development mode, we point vite to the source of the local libraries, so the HMR works correctly.
    // Reference: https://github.com/vitejs/vite/discussions/7155#discussioncomment-4121062
    return {
      'sera-db': fileURLToPath(new URL('../db/src/index.ts', import.meta.url)),
    }
  })();

  return {
    plugins: [dts({ tsconfigPath: "./tsconfig.build.json" })],
    resolve: {
      alias: {
        ...localLibraryAlias
      },
    },
    build: {
      lib: {
        entry: resolve(__dirname, "src/index.ts"),
        name: "sera-components",
        // the proper extensions will be added
        fileName: "index",
      },
      rollupOptions: {
        // make sure to externalize deps that shouldn't be bundled
        // into your library
        external: [
          "@mantine/core",
          "@mantine/form",
          "@mantine/dates",
          "dayjs",
          "react",
          "react-dom",
          "react-imask",
          "@tabler/icons-react",
          "sera-db",
          "mobx-react-lite",
          "throttle-debounce",
        ],
        output: {
          // Provide global variables to use in the UMD build
          // for externalized deps
          globals: {
            "@mantine/core": "@mantine/core",
            "@mantine/form": "@mantine/form",
            "@mantine/dates": "@mantine/dates",
            "dayjs": "dayjs",
            "react": "React",
            "react-dom": "ReactDOM",
            "react-imask": "ReactIMask",
            "@tabler/icons-react": "@tabler/icons-react",
            "sera-db": "sera-db",
            "mobx-react-lite": "mobx-react-lite",
            "throttle-debounce": "throttle-debounce",
          },
        },
      },
    },
  }
});
