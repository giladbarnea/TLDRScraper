Title: Installation – React

URL Source: https://react.dev/learn/react-compiler/installation

Published Time: Wed, 29 Oct 2025 18:50:45 GMT

Markdown Content:
This guide will help you install and configure React Compiler in your React application.

### You will learn

*   How to install React Compiler
*   Basic configuration for different build tools
*   How to verify your setup is working

Prerequisites [](https://react.dev/learn/react-compiler/installation#prerequisites "Link for Prerequisites ")
-------------------------------------------------------------------------------------------------------------

React Compiler is designed to work best with React 19, but it also supports React 17 and 18. Learn more about [React version compatibility](https://react.dev/reference/react-compiler/target).

Installation [](https://react.dev/learn/react-compiler/installation#installation "Link for Installation ")
----------------------------------------------------------------------------------------------------------

Install React Compiler as a `devDependency`:

Terminal

npm install -D babel-plugin-react-compiler@latest

Or with Yarn:

Terminal

yarn add -D babel-plugin-react-compiler@latest

Or with pnpm:

Terminal

pnpm install -D babel-plugin-react-compiler@latest

Basic Setup [](https://react.dev/learn/react-compiler/installation#basic-setup "Link for Basic Setup ")
-------------------------------------------------------------------------------------------------------

React Compiler is designed to work by default without any configuration. However, if you need to configure it in special circumstances (for example, to target React versions below 19), refer to the [compiler options reference](https://react.dev/reference/react-compiler/configuration).

The setup process depends on your build tool. React Compiler includes a Babel plugin that integrates with your build pipeline.

### Pitfall

React Compiler must run **first** in your Babel plugin pipeline. The compiler needs the original source information for proper analysis, so it must process your code before other transformations.

### Babel [](https://react.dev/learn/react-compiler/installation#babel "Link for Babel ")

Create or update your `babel.config.js`:

`module.exports = {plugins: ['babel-plugin-react-compiler', // must run first!// ... other plugins],// ... other config};`

### Vite [](https://react.dev/learn/react-compiler/installation#vite "Link for Vite ")

If you use Vite, you can add the plugin to vite-plugin-react:

`// vite.config.jsimport { defineConfig } from 'vite';import react from '@vitejs/plugin-react';export default defineConfig({plugins: [react({babel: {plugins: ['babel-plugin-react-compiler'],},}),],});`

Alternatively, if you prefer a separate Babel plugin for Vite:

Terminal

npm install -D vite-plugin-babel

`// vite.config.jsimport babel from 'vite-plugin-babel';import { defineConfig } from 'vite';import react from '@vitejs/plugin-react';export default defineConfig({plugins: [react(),babel({babelConfig: {plugins: ['babel-plugin-react-compiler'],},}),],});`

### Next.js [](https://react.dev/learn/react-compiler/installation#usage-with-nextjs "Link for Next.js ")

Please refer to the [Next.js docs](https://nextjs.org/docs/app/api-reference/next-config-js/reactCompiler) for more information.

### React Router [](https://react.dev/learn/react-compiler/installation#usage-with-react-router "Link for React Router ")

Install `vite-plugin-babel`, and add the compiler’s Babel plugin to it:

Terminal

npm install vite-plugin-babel

`// vite.config.jsimport { defineConfig } from "vite";import babel from "vite-plugin-babel";import { reactRouter } from "@react-router/dev/vite";const ReactCompilerConfig = { /* ... */ };export default defineConfig({plugins: [reactRouter(),babel({filter: /\.[jt]sx?$/,babelConfig: {presets: ["@babel/preset-typescript"], // if you use TypeScriptplugins: [["babel-plugin-react-compiler", ReactCompilerConfig],],},}),],});`

### Webpack [](https://react.dev/learn/react-compiler/installation#usage-with-webpack "Link for Webpack ")

A community webpack loader is [now available here](https://github.com/SukkaW/react-compiler-webpack).

### Expo [](https://react.dev/learn/react-compiler/installation#usage-with-expo "Link for Expo ")

Please refer to [Expo’s docs](https://docs.expo.dev/guides/react-compiler/) to enable and use the React Compiler in Expo apps.

### Metro (React Native) [](https://react.dev/learn/react-compiler/installation#usage-with-react-native-metro "Link for Metro (React Native) ")

React Native uses Babel via Metro, so refer to the [Usage with Babel](https://react.dev/learn/react-compiler/installation#babel) section for installation instructions.

### Rspack [](https://react.dev/learn/react-compiler/installation#usage-with-rspack "Link for Rspack ")

Please refer to [Rspack’s docs](https://rspack.dev/guide/tech/react#react-compiler) to enable and use the React Compiler in Rspack apps.

### Rsbuild [](https://react.dev/learn/react-compiler/installation#usage-with-rsbuild "Link for Rsbuild ")

Please refer to [Rsbuild’s docs](https://rsbuild.dev/guide/framework/react#react-compiler) to enable and use the React Compiler in Rsbuild apps.

ESLint Integration [](https://react.dev/learn/react-compiler/installation#eslint-integration "Link for ESLint Integration ")
----------------------------------------------------------------------------------------------------------------------------

React Compiler includes an ESLint rule that helps identify code that can’t be optimized. When the ESLint rule reports an error, it means the compiler will skip optimizing that specific component or hook. This is safe: the compiler will continue optimizing other parts of your codebase. You don’t need to fix all violations immediately. Address them at your own pace to gradually increase the number of optimized components.

Install the ESLint plugin:

Terminal

npm install -D eslint-plugin-react-hooks@latest

If you haven’t already configured eslint-plugin-react-hooks, follow the [installation instructions in the readme](https://github.com/facebook/react/blob/main/packages/eslint-plugin-react-hooks/README.md#installation). The compiler rules are available in the `recommended-latest` preset.

The ESLint rule will:

*   Identify violations of the [Rules of React](https://react.dev/reference/rules)
*   Show which components can’t be optimized
*   Provide helpful error messages for fixing issues

Verify Your Setup [](https://react.dev/learn/react-compiler/installation#verify-your-setup "Link for Verify Your Setup ")
-------------------------------------------------------------------------------------------------------------------------

After installation, verify that React Compiler is working correctly.

### Check React DevTools [](https://react.dev/learn/react-compiler/installation#check-react-devtools "Link for Check React DevTools ")

Components optimized by React Compiler will show a “Memo ✨” badge in React DevTools:

1.   Install the [React Developer Tools](https://react.dev/learn/react-developer-tools) browser extension
2.   Open your app in development mode
3.   Open React DevTools
4.   Look for the ✨ emoji next to component names

If the compiler is working:

*   Components will show a “Memo ✨” badge in React DevTools
*   Expensive calculations will be automatically memoized
*   No manual `useMemo` is required

### Check Build Output [](https://react.dev/learn/react-compiler/installation#check-build-output "Link for Check Build Output ")

You can also verify the compiler is running by checking your build output. The compiled code will include automatic memoization logic that the compiler adds automatically.

`import { c as _c } from "react/compiler-runtime";export default function MyApp() {const $ = _c(1);let t0;if ($[0] === Symbol.for("react.memo_cache_sentinel")) {t0 = <div>Hello World</div>;$[0] = t0;} else {t0 = $[0];}return t0;}`

Troubleshooting [](https://react.dev/learn/react-compiler/installation#troubleshooting "Link for Troubleshooting ")
-------------------------------------------------------------------------------------------------------------------

### Opting out specific components [](https://react.dev/learn/react-compiler/installation#opting-out-specific-components "Link for Opting out specific components ")

If a component is causing issues after compilation, you can temporarily opt it out using the `"use no memo"` directive:

`function ProblematicComponent() {"use no memo";// Component code here}`

This tells the compiler to skip optimization for this specific component. You should fix the underlying issue and remove the directive once resolved.

For more troubleshooting help, see the [debugging guide](https://react.dev/learn/react-compiler/debugging).

Next Steps [](https://react.dev/learn/react-compiler/installation#next-steps "Link for Next Steps ")
----------------------------------------------------------------------------------------------------

Now that you have React Compiler installed, learn more about:

*   [React version compatibility](https://react.dev/reference/react-compiler/target) for React 17 and 18
*   [Configuration options](https://react.dev/reference/react-compiler/configuration) to customize the compiler
*   [Incremental adoption strategies](https://react.dev/learn/react-compiler/incremental-adoption) for existing codebases
*   [Debugging techniques](https://react.dev/learn/react-compiler/debugging) for troubleshooting issues
*   [Compiling Libraries guide](https://react.dev/reference/react-compiler/compiling-libraries) for compiling your React library
