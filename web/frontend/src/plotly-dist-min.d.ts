/**
 * Ambient type declaration for plotly.js-dist-min.
 *
 * plotly.js-dist-min is the minified, self-contained bundle of Plotly.
 * It does not ship its own .d.ts file. We borrow the types from the full
 * @types/plotly.js package (installed as a peer of @types/react-plotly.js).
 *
 * This makes `import Plotly from "plotly.js-dist-min"` fully type-safe.
 */

declare module "plotly.js-dist-min" {
  // Re-export everything from the full plotly.js type declarations
  export * from "plotly.js";
  export { default } from "plotly.js";
}
