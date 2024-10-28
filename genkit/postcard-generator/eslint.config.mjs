import path from "node:path";
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";
import { fixupConfigRules } from "@eslint/compat";
import stylistic from "@stylistic/eslint-plugin";
import pluginJs from "@eslint/js";
import tseslint from "typescript-eslint";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: js.configs.recommended,
  allConfig: js.configs.all,
});

const patchedConfig = fixupConfigRules([...compat.extends("next/core-web-vitals")]);

const config = [
  ...patchedConfig,
  pluginJs.configs.recommended,
  ...tseslint.configs.recommended,
  stylistic.configs["recommended-flat"],
  stylistic.configs.customize({
    quotes: "double",
    semi: true,
    indent: 2,
  }),
  { ignores: [".next/*"] },
];

export default config;
