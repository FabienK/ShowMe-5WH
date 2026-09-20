# 001 — Add press feedback to the base `button` element

- **Status**: DONE
- **Commit**: e1ba50f
- **Severity**: HIGH
- **Category**: Physicality & origin (press feedback) / Missed opportunities
- **Estimated scope**: 1 file, ~10 lines added (`frontend/src/index.css`)

## Problem

The app has no click/press feedback anywhere except two hand-built exceptions
(`.btn` and `.mode-selector__tile`, both HomePage-only). Every other clickable
`<button>` in the app — option-list choices, icon-buttons, history rows,
model-selector options, batch mode toggles, the plain action buttons on
`ResultPage` — relies on the bare `button` element rule in
`frontend/src/index.css:102-119`, which has no `transition` at all and no
`:active` state. Hover only flips `border-color` instantly:

```css
/* frontend/src/index.css:102-119 — current */
button {
  font: inherit;
  padding: 0.65rem 1.1rem;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-h);
  cursor: pointer;
}

button:hover:not(:disabled) {
  border-color: var(--accent);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

This is a real gap, not a style nit: nearly every interactive surface in the
app is a plain `<button>` — confirmed by grep, only 4 buttons in
`frontend/src/pages/HomePage.tsx:97,102,137,140` carry the `.btn` class.
Everything else — `frontend/src/components/OptionList.tsx:14`,
`frontend/src/components/QuestionCard.tsx:60` (dice icon button),
`frontend/src/pages/ResultPage.tsx:114,143,146,149,173` (image zoom,
regenerate/modify/restart, lightbox close),
`frontend/src/pages/HistoryPage.tsx:23` (`.history-page__row`),
`frontend/src/pages/BatchComposerPage.tsx:78,222` (remove item, add item),
`.model-selector__option`, `.batch-composer-page__mode-button`, every
`.icon-button` — has zero feedback on click. Because this is hit tens of
times a day across the whole app, a single small, fast, subtle fix here has
outsized leverage: one CSS change fixes click feedback everywhere at once.

## Target

Per `AUDIT.md` §2/§3: press feedback duration is 100–160ms, scale stays in
0.95–0.98, easing is `ease-out` for a responsive-feeling press. This repo has
no `--ease-*` tokens defined yet (`index.css` only uses bare `ease`/`linear`
inline) — do not invent one for this plan; use the plain `ease-out` keyword,
consistent with the existing `.btn` and `.mode-selector__tile` transitions
which also use bare `ease` keywords, not custom cubic-beziers.

```css
/* frontend/src/index.css:102-119 — target */
button {
  font: inherit;
  padding: 0.65rem 1.1rem;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-h);
  cursor: pointer;
  transition:
    transform 120ms ease-out,
    border-color 120ms ease-out;
}

button:hover:not(:disabled) {
  border-color: var(--accent);
}

button:active:not(:disabled) {
  transform: scale(0.97);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (prefers-reduced-motion: reduce) {
  button {
    transition: border-color 120ms ease-out;
  }

  button:active:not(:disabled) {
    transform: none;
  }
}
```

## Repo conventions to follow

- Transitions in this file are always written as a multi-line comma list
  when more than one property animates — follow the existing pattern at
  `frontend/src/index.css:132-138` (`.btn`) exactly: one property per line,
  trailing comma except the last, semicolon after the final value.
- Press/hover scale precedent already exists at
  `frontend/src/index.css:340-364` (`.mode-selector__tile`):
  `transform: translateY(-3px)` on hover with
  `transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;`
  — same shape of rule, same keyword-easing style. Mirror that style (bare
  `ease-out` keyword, not a token) rather than introducing a new pattern.
- `frontend/src/index.css` currently has no `@media (prefers-reduced-motion: reduce)`
  block anywhere in the file — this plan introduces the first one. Keep it
  directly after the `button` rules it modifies, not hoisted to `:root`.

## Steps

1. Open `frontend/src/index.css` and locate the `button { … }` rule at line
   102. Add a `transition` declaration for `transform` and `border-color`,
   both `120ms ease-out`, as shown in Target above.
2. Immediately after the existing `button:hover:not(:disabled) { border-color: var(--accent); }`
   rule (currently line 112-114), add a new rule:
   `button:active:not(:disabled) { transform: scale(0.97); }`. Use `:not(:disabled)`
   so disabled buttons (which already show `cursor: not-allowed` via the
   `button:disabled` rule) never scale.
3. After the `button:disabled { … }` rule (currently line 116-119), add the
   `@media (prefers-reduced-motion: reduce)` block from Target: keep the
   `border-color` transition (it aids comprehension, per AUDIT.md §6) but
   set `button:active:not(:disabled) { transform: none; }` so no scale
   happens under reduced motion.
4. Do not touch `.btn`, `.btn--primary`, `.btn--secondary`, or
   `.mode-selector__tile` — they already have their own hover transforms
   (`translateY(-1px)` / `translateY(-3px)`) and are out of scope (see
   Boundaries).

## Boundaries

- Do NOT modify `.btn`, `.btn--primary`, `.btn--secondary`
  (`frontend/src/index.css:121-167`) or `.mode-selector__tile`
  (`frontend/src/index.css:340-364`). Both already have hover-driven
  `transform` (`translateY`), and stacking a `:active` scale on top of
  them via the base `button` rule would fight their existing hover
  transform under a specificity conflict that needs its own design pass —
  out of scope for this plan. (Flag as a follow-up finding, don't attempt
  a fix here.)
- Do NOT touch any component/page files — this is a single CSS-file change.
- Do NOT add a design token (`--ease-out`, `--duration-*`, etc.) in this
  plan. The repo has no such tokens today; introducing one is a separate,
  larger cohesion change (AUDIT.md §7) that should touch the whole file
  deliberately, not be smuggled into a press-feedback fix.
- Do NOT change `transition: all` anywhere — this file doesn't currently
  use `transition: all` on the base `button` rule, and the target above
  must stay as an explicit property list, not `all`.
- If the `button` rule at `frontend/src/index.css:102-119` doesn't match
  the current-code excerpt above (drift since commit `e1ba50f`), STOP and
  report instead of improvising.

## Verification

- **Mechanical**: from `frontend/`, run `npm run lint` and `npm run build`
  (per `init/etat.md`, both are expected to stay clean —
  `cd frontend && npm run test && npm run build && npm run lint`). No
  TypeScript/JS files change, so `npm run test` should be unaffected; run
  it anyway to confirm no snapshot regressions from the new CSS classes.
- **Feel check**: start the dev server (`npm run dev` or the project's
  existing preview task) and in the browser:
  - Click and hold an `OptionList` item (any question's answer tile) —
    confirm it visibly shrinks to ~97% while held, and springs back on
    release. It should feel instant, not springy or slow.
  - Click and hold a plain `.icon-button` (e.g. the home icon in
    `QuestionPage`'s toolbar) — same check.
  - Click a disabled button (e.g. `ScriptPreviewPage`'s confirm button
    before a model is selected) — confirm it does NOT scale on
    mousedown.
  - In DevTools, set the Animations panel playback to 10% and trigger a
    press — confirm the scale animates smoothly over ~120ms with no
    layout shift (only `transform` changes, nothing reflows).
  - Toggle `prefers-reduced-motion: reduce` in the Rendering panel,
    repeat the click-and-hold on an `OptionList` item — confirm the
    button no longer scales, but the border-color hover feedback still
    works.
  - Spot-check one HomePage `.btn` button (e.g. "Générer") to confirm its
    existing hover lift (`translateY(-1px)`) still works unchanged — this
    plan must not regress it.
- **Done when**: every plain `<button>` across `OptionList`, icon-buttons,
  `HistoryPage` rows, `ModelSelector` options, and the batch mode toggle
  buttons shows a ~97% scale press-and-release on click, disabled buttons
  never scale, reduced-motion users get color feedback without movement,
  and `.btn`/`.mode-selector__tile` hover behavior is unchanged.
