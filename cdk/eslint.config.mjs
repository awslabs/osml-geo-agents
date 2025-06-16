import eslint from "@eslint/js";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";
import prettier from "eslint-plugin-prettier";
import eslintConfigPrettier from "eslint-config-prettier";
import jest from "eslint-plugin-jest";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import importPlugin from "eslint-plugin-import";
import promise from "eslint-plugin-promise";

export default [
  eslint.configs.recommended,
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        project: "./tsconfig.json",
        ecmaVersion: 2020,
        sourceType: "module"
      },
      globals: {
        process: true,
        console: true,
        __dirname: true,
        module: true
      }
    },
    plugins: {
      "@typescript-eslint": tseslint,
      prettier: prettier,
      jest: jest,
      "simple-import-sort": simpleImportSort,
      import: importPlugin,
      promise: promise
    },
    rules: {
      ...tseslint.configs["recommended"].rules,
      ...tseslint.configs["recommended-requiring-type-checking"].rules,
      ...importPlugin.configs["typescript"].rules,
      ...promise.configs.recommended.rules,
      ...jest.configs.recommended.rules,
      ...jest.configs.style.rules,
      "prettier/prettier": "error",
      "simple-import-sort/imports": "error",
      "import/default": "off",
      "import/order": "off",
      "require-await": "off",
      "@typescript-eslint/no-unused-expressions": [
        "error",
        { allowTernary: true }
      ],
      "@typescript-eslint/no-unsafe-assignment": "warn",
      "@typescript-eslint/interface-name-prefix": "off",
      "@typescript-eslint/no-empty-interface": "off",
      "@typescript-eslint/no-inferrable-types": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
      "@typescript-eslint/require-await": "error",
      "@typescript-eslint/no-empty-function": "off",
      "jest/no-done-callback": "off",
      "jest/no-conditional-expect": "off"
    }
  },
  {
    files: ["**/*.test.ts", "**/*.spec.ts"],
    languageOptions: {
      globals: {
        describe: true,
        test: true,
        expect: true,
        beforeAll: true,
        jest: true
      }
    }
  },
  eslintConfigPrettier
];
