# Cowork dashboard JS — `static_cw/`

Static assets for the Cowork dashboard, served as-is at `/cw-static/*`
(mounted in `app.py`). **No build step, no bundler** — the `.js` files
here are both the source and the served asset.

## Testing dashboard JS

Dashboard interactivity used to live as inline `<script>` blocks in Jinja
templates, which can't be unit-tested. The pattern below makes it
testable without adding a build step. `batch-panel.js` is the reference
implementation (see `specs/dashboard-js-testing/`).

**The rule: pure logic goes in a module here; the template keeps only a
DOM-glue shim.**

1. **Extract pure functions** into a `*.js` module in this directory —
   DOM-free and `window`-free (so Vitest imports it in Node, no jsdom).
   A frame/event in, a plain view-model or decision out. All the
   branching lives here.

   ```js
   // my-panel.js
   export function myView(frame) { /* → { visible, label, … } */ }
   ```

2. **Test it** in a colocated `*.test.js` with Vitest:

   ```js
   import { myView } from "./my-panel.js";
   it("hides on empty", () => expect(myView({state:"none"})).toEqual({visible:false}));
   ```

3. **Shrink the template** to a `<script type="module">` that imports the
   module and only touches the DOM — no branching worth testing:

   ```html
   <script type="module">
     import { myView } from '/cw-static/my-panel.js';
     const els = { /* querySelector */ };
     function apply(v) { /* set hidden / textContent / styles from v */ }
     // …wire events, call apply(myView(frame))…
   </script>
   ```

## Running the tests

The dashboard modules are covered by the **editor-frontend** Vitest
project (one project, one CI job for all attune-gui frontend JS). Its
`vitest.config.ts` includes `../sidecar/attune_gui/static_cw/**/*.test.js`.

```bash
cd editor-frontend && npm test        # runs editor + dashboard suites
```

The `frontend (Vitest)` CI job runs these on every PR.

## Migrating the remaining inline blocks

Several dashboard templates still carry inline `<script>` logic (the
living-docs poller, command runner, etc.). Migrate them to this pattern
opportunistically — extract the pure half, test it, leave a glue shim.
Keep each migration behavior-preserving (verify the page renders
identically).
