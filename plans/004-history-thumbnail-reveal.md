# 004 — Fade in history thumbnails as they resolve

- **Status**: DONE
- **Commit**: e1ba50f
- **Severity**: LOW
- **Category**: Missed opportunities (state indication) / Physicality & origin
- **Estimated scope**: 1 file, ~6 lines added (`frontend/src/index.css`)

## Problem

`BatchDetailView` polls `/api/batches/:id` every 3s (`frontend/src/pages/HistoryPage.tsx:76-100`)
while a batch is running. Each item's thumbnail is rendered by
`BatchItemThumbnail`, which returns a **different root element type**
depending on `item.status`:

```tsx
/* frontend/src/pages/HistoryPage.tsx:37-62 — current, unchanged by this plan */
function BatchItemThumbnail({ item }: { item: BatchDetail["items"][number] }) {
  if (item.status === "success" && item.image_path) {
    return (
      <a
        className="history-page__thumbnail"
        href={`/generated/${item.image_path}`}
        target="_blank"
        rel="noreferrer"
      >
        <img src={`/generated/${item.image_path}`} alt={item.request.script} />
      </a>
    );
  }
  if (item.status === "error") {
    return (
      <div className="history-page__thumbnail history-page__thumbnail--error">
        <p>{item.error_detail ?? "Erreur inconnue"}</p>
      </div>
    );
  }
  return (
    <div className="history-page__thumbnail history-page__thumbnail--pending">
      {item.status === "running" ? <Loader label="En cours…" /> : "En attente"}
    </div>
  );
}
```

Because the returned root element changes type (`<div>` → `<a>`, or
`<div>` → `<div className="…--error">`) at the same tree position inside
`.history-page__detail-item` (`frontend/src/pages/HistoryPage.tsx:116`,
`key={item.index}` stays stable on the parent, but that doesn't matter here
— React always fully unmounts and remounts a node when its element **type**
changes between renders, regardless of the parent's key), each thumbnail's
final state — the actual generated image, or an error card — snaps in
instantly on the poll tick that resolves it. There's no indication that
anything just changed; the user has to notice a static image replaced a
static placeholder.

```css
/* frontend/src/index.css:1275-1290 — current */
.history-page__thumbnail {
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
}

.history-page__thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
```

Per `AUDIT.md` §8, this is a state change that teleports and would benefit
from a brief transition to avoid the jarring snap — and per §1 it's an
occasional-frequency surface (watching an overnight batch progress), well
within the standard-animation tier.

## Target

Per the earlier find-animation-opportunities report for this exact element:
**opacity only** — this is data the user is scanning (is this item done? did
it error?), not a celebratory reveal, so no scale or translate, unlike plan
003's result cards. Because the element genuinely remounts on every status
change (confirmed above), `@starting-style` needs no JS support at all here
— same mechanism as plan 003, simpler still since there's only one property.

Note that `.history-page__thumbnail--pending` (`frontend/src/index.css:1300-1304`)
already sets `opacity: 0.7` as its static resting look — this is intentional
existing behavior (a dimmed placeholder), not something this plan should
change.

**Empirically verified while implementing this plan**: a single
`@starting-style { opacity: 0; }` on the base `.history-page__thumbnail`
rule is **not** enough to cover the `--pending` variant. `@starting-style`
declarations participate in the normal CSS cascade (same specificity/source-order
tie-breaking as regular rules) rather than unconditionally overriding every
property for the starting snapshot. Since `.history-page__thumbnail--pending
{ opacity: 0.7; }` is a normal (non-starting-style) rule with equal
specificity to the base `@starting-style` rule and comes later in source
order, it wins the starting-style computation too — meaning, without a
dedicated fix, pending thumbnails would render at `opacity: 0.7` immediately
on mount with no fade at all (confirmed by reading `getComputedStyle(...).opacity`
synchronously after inserting a fresh `.history-page__thumbnail--pending`
node: it read `0.7`, not `0`, until a second, variant-specific
`@starting-style` rule was added **after** the normal `--pending` rule in
source order — only then did it correctly read `0` immediately after mount
and `0.7` ~350ms later). Success and error thumbnails were unaffected by
this (neither sets its own `opacity`, so the base `@starting-style` rule
applies to them cleanly) — confirmed the same way, both reading `0`
immediately and `1` ~350ms later.

This plan therefore adds a second, `--pending`-specific `@starting-style`
rule, placed after `.history-page__thumbnail--pending`'s normal rule.

```css
/* frontend/src/index.css:1275-1290 — target */
.history-page__thumbnail {
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  transition: opacity 300ms ease-out;
}

@starting-style {
  .history-page__thumbnail {
    opacity: 0;
  }
}

.history-page__thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
```

```css
/* frontend/src/index.css:1307-1311 (.history-page__thumbnail--pending) — target: add a starting-style rule immediately after it */
.history-page__thumbnail--pending {
  font-size: 0.8rem;
  color: var(--text);
  opacity: 0.7;
}

/* Doit rester après la règle --pending ci-dessus : à spécificité égale, une
   déclaration @starting-style placée avant une règle normale ne l'emporte
   pas sur le calcul de l'état de départ (vérifié empiriquement — sans ce
   second bloc, les vignettes en attente n'ont aucun fondu, elles restent
   bloquées à 0.7 dès le montage). */
@starting-style {
  .history-page__thumbnail--pending {
    opacity: 0;
  }
}
```

No `prefers-reduced-motion` block is needed for this plan: per `AUDIT.md`
§6, reduced motion means dropping *movement*, not opacity/color feedback —
this transition is opacity-only already, so it's reduced-motion-safe as
written (same reasoning as the existing ungated opacity transitions already
in this file, e.g. `.result-page__image-zoom-hint` at
`frontend/src/index.css:895-896`).

## Repo conventions to follow

- This is the second `@starting-style` usage in the file (plan 003 added
  the first, for `.result-page__result`) — same top-level at-rule form (not
  nested), placed immediately after the rule it augments, exactly like
  `frontend/src/index.css:850-863`.
- Single-property transitions in this file are written as one line, e.g.
  `.result-page__image-zoom-hint { transition: opacity 0.15s ease; }`
  (`frontend/src/index.css:896`) — follow that exact single-line style here
  rather than the multi-line comma form used for multi-property transitions
  (plans 001/002/003 all use the multi-line form only because they animate
  more than one property).

## Steps

1. In `frontend/src/index.css`, in the `.history-page__thumbnail` rule
   (currently lines 1275-1284), add `transition: opacity 300ms ease-out;`
   as the last declaration before the closing brace.
2. Immediately after that rule (before `.history-page__thumbnail img`,
   currently starting at line 1286), insert:
   ```css
   @starting-style {
     .history-page__thumbnail {
       opacity: 0;
     }
   }
   ```
3. Leave `.history-page__thumbnail img` and `.history-page__thumbnail--error`
   untouched — neither needs a change (see Problem/Target: `--error` sets no
   `opacity` of its own, so the base `@starting-style` rule already covers
   it correctly).
4. Immediately after `.history-page__thumbnail--pending`'s existing rule
   (currently lines 1307-1311, `opacity: 0.7;`), add the second,
   variant-specific `@starting-style` block shown in Target, including the
   explanatory comment — this ordering (after the normal rule, not before
   or grouped with the base `@starting-style` block near the top) is
   required for the fade to actually apply to pending thumbnails; see
   Problem/Target for the empirical reasoning.
5. Do not touch `frontend/src/pages/HistoryPage.tsx` — no JSX or state
   changes are needed; the existing type-changing conditional render in
   `BatchItemThumbnail` already produces a fresh mount on every status
   transition.

## Boundaries

- Do NOT change `.history-page__thumbnail--pending`'s existing
  `opacity: 0.7` resting value — that's deliberate, pre-existing dimming,
  not part of this plan.
- Do NOT add scale or transform — this element is data the user is
  scanning; keep it to opacity only, per the earlier report's explicit
  guidance for this specific element.
- Do NOT touch `.history-page__detail-grid`, `.history-page__detail-item`,
  or `.history-page__detail-model` — those are layout/typography, unrelated
  to the thumbnail's own state transition.
- Do NOT touch the accordion expand/collapse behavior in `HistoryPage`
  (`BatchRow`'s `onOpen` toggling `openBatchId`) — that was explicitly
  rejected in the earlier find-animation-opportunities report (unpredictable
  height, active polling loop) and is out of scope here.
- If the current-code excerpts above don't match what's on disk (drift
  since commit `e1ba50f`), STOP and report instead of improvising.

## Verification

- **Mechanical**: from `frontend/`, run `npm run lint`, `npm run build`, and
  `npm run test`. All three must stay clean — CSS-only change, no
  TypeScript surface affected.
- **Feel check**: this needs a batch with at least one still-pending or
  still-running item, which requires the backend and ComfyUI running (per
  `init/etat.md`) — if that isn't available, replicate the exact CSS in a
  static HTML file that swaps a `<div class="history-page__thumbnail
  history-page__thumbnail--pending">` for an `<a class="history-page__thumbnail">`
  (or the `--error` variant) at the same DOM position on a button click,
  served over `http://localhost` (not `file://`), and check:
  - The incoming thumbnail fades in over ~300ms rather than snapping to
    visible — confirm by reading `getComputedStyle(...).opacity`
    immediately after the swap (should read `0` or a low interpolated
    value) and again ~350ms later (should read the variant's resting
    value: `1` for success/error, `0.7` for pending).
  - A pending thumbnail (which rests at `opacity: 0.7`, not `1`) fades in
    to exactly `0.7`, not `1` — confirms the per-element interpolation
    target described in Target works as expected, not a hardcoded `1`.
  - Sibling thumbnails already showing their final image do NOT replay any
    fade when a different item's status resolves (each is an independent
    element).
  - In DevTools Animations panel at 10% playback, confirm only `opacity`
    animates — no layout shift in the surrounding `auto-fill` grid.
- **Done when**: every thumbnail — success, error, or pending — fades in to
  its correct resting opacity on mount/remount, with no changes to the
  pending variant's existing dimmed look and no animation on the grid
  layout itself.
