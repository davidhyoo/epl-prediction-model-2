import next from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

/** Flat ESLint config for Next.js 16 (App Router) + TypeScript. */
const eslintConfig = [
  ...next,
  ...typescript,
  {
    // Pin the React version explicitly. eslint-plugin-react's auto-detection
    // crashes under ESLint 10 (contextOrFilename.getFilename is not a function),
    // so we short-circuit it by declaring the version here.
    settings: {
      react: {
        version: "19.2",
      },
    },
  },
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "out/**",
      "coverage/**",
      "public/**",
      "ml/**",
      "data/**",
      "next-env.d.ts",
    ],
  },
];

export default eslintConfig;
