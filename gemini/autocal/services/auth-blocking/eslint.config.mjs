import globals from "globals";
import pluginJs from "@eslint/js";
import tseslint from "typescript-eslint";
import eslintPluginPrettierRecommended from "eslint-plugin-prettier/recommended";

export default [
  { files: ["src/*.{js,mjs,cjs,ts}"] },
  { files: ["**/*.ts"], languageOptions: { sourceType: "commonjs" } },
  { languageOptions: { globals: globals.node } },
  { ignores: ["lib/*"] },
  pluginJs.configs.recommended,
  ...tseslint.configs.recommended,
  eslintPluginPrettierRecommended,
];
