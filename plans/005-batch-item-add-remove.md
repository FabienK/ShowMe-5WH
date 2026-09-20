# 005 — Animate batch item add/remove

- **Status**: DONE
- **Commit**: e1ba50f
- **Severity**: LOW
- **Category**: Missed opportunities (preventing a jarring change) / Interruptibility
- **Estimated scope**: 3 files (`frontend/src/state/useBatchComposer.ts`,
  `frontend/src/pages/BatchComposerPage.tsx`, `frontend/src/index.css`),
  ~40 lines added/changed

## Problem

`BatchComposerPage` renders one `<li className="batch-composer-page__item">`
per draft item, backed by `useBatchComposer`'s `items` state
(`frontend/src/state/useBatchComposer.ts:60`). Adding or removing an item
gives that `<li>` no transition at all — it snaps into or out of the list
instantly.

```ts
/* frontend/src/state/useBatchComposer.ts:75-81 — current */
const addItem = useCallback(() => {
  setItems((prev) => [...prev, emptyItem()]);
}, []);

const removeItem = useCallback((id: string) => {
  setItems((prev) => (prev.length > 1 ? prev.filter((item) => item.id !== id) : prev));
}, []);
```

```tsx
/* frontend/src/pages/BatchComposerPage.tsx:72-88 — current */
<ul className="batch-composer-page__items">
  {items.map((item, index) => (
    <li className="batch-composer-page__item" key={item.id}>
      <div className="batch-composer-page__item-header">
        <h3>Item {index + 1}</h3>
        {items.length > 1 && (
          <button
            type="button"
            className="icon-button"
            onClick={() => removeItem(item.id)}
            aria-label="Supprimer cet item"
            title="Supprimer cet item"
          >
            <CloseIcon />
          </button>
        )}
      </div>
```

```css
/* frontend/src/index.css:1097-1105 — current */
.batch-composer-page__item {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem;
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
```

Each item gets a fresh, stable `id` from `makeId()` (`frontend/src/state/useBatchComposer.ts:36-40,42-57`),
used as the React `key` — so `addItem` genuinely mounts a new `<li>` (a
`@starting-style` entrance works with no JS, same mechanism as plan 003).
`removeItem`, however, currently calls `setItems` synchronously, which
removes the `<li>` from the DOM on the same render — there is no window for
an exit transition to play, the same structural problem plan 002 solved for
the lightbox. This plan applies the same pattern here: a `removingIds` set
that marks an item as "leaving" (triggering the CSS exit transition) before
the item is actually filtered out of `items` once the transition has had
time to finish.

Per `AUDIT.md` §8, this is a state change that teleports and would benefit
from a brief transition; per §1, composing a batch is an occasional action
(a handful of items per session), well within the standard-animation tier.

## Target

Per `AUDIT.md` §2, duration budget for this kind of UI is under 300ms; this
plan mirrors the earlier find-animation-opportunities report's suggested
values for this exact element (`translateY(-8px)`-style entrance) but uses
`translateY(8px)` — positive, not negative — to match this codebase's
established convention from plan 003 (`.result-page__result`, which settles
*upward* into place, i.e. starts slightly below its resting position). Per
§3, never `scale(0)` — this plan uses opacity + translate only, no scale
(list-item rows reflow vertically; a scale would fight the vertical
motion). Entrance and exit reuse the exact same transition, applied
symmetrically (§8: "exit a different way than they entered → symmetric
paths" — here, literally the reverse of the same path).

```css
/* frontend/src/index.css:1097-1105 — target */
.batch-composer-page__item {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem;
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  opacity: 1;
  transform: none;
  transition:
    transform 220ms ease-out,
    opacity 180ms ease-out;
}

@starting-style {
  .batch-composer-page__item {
    opacity: 0;
    transform: translateY(8px);
  }
}

.batch-composer-page__item--leaving {
  opacity: 0;
  transform: translateY(8px);
  pointer-events: none;
}
```

`.batch-composer-page__item--leaving` is a normal (non-`@starting-style`)
rule toggled by a class change on an **already-mounted** element — this is
an ordinary CSS transition (old declared value → new declared value), not a
mount event, so it does not have the same-specificity/source-order pitfall
that plan 004 hit with `@starting-style` (that issue only applies to the
one-time starting-style snapshot computed when an element is first added to
the DOM). `pointer-events: none` on the leaving state prevents any click
(including a second click on that item's own remove button) while it's
fading out.

```ts
/* frontend/src/state/useBatchComposer.ts:1,59-81 — target */
import { useCallback, useEffect, useRef, useState } from "react";
/* … existing imports unchanged … */

export function useBatchComposer() {
  const [items, setItems] = useState<BatchDraftItem[]>([emptyItem()]);
  const [questions, setQuestions] = useState<QuestionDefinition[]>([]);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());
  const removeTimeouts = useRef<Record<string, number>>({});

  // Durée alignée sur la plus longue transition CSS de
  // .batch-composer-page__item (transform, 220ms) pour laisser l'animation
  // de sortie finir avant le retrait réel de l'item.
  const ITEM_EXIT_MS = 220;

  useEffect(() => {
    return () => {
      Object.values(removeTimeouts.current).forEach((timeoutId) => window.clearTimeout(timeoutId));
    };
  }, []);

  /* … existing useEffect for api.getQuestions() unchanged … */

  const addItem = useCallback(() => {
    setItems((prev) => [...prev, emptyItem()]);
  }, []);

  const removeItem = useCallback(
    (id: string) => {
      if (removingIds.has(id)) return;
      const remainingCount = items.length - removingIds.size;
      if (remainingCount <= 1) return;

      setRemovingIds((prev) => new Set(prev).add(id));
      removeTimeouts.current[id] = window.setTimeout(() => {
        setItems((prev) => prev.filter((item) => item.id !== id));
        setRemovingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        delete removeTimeouts.current[id];
      }, ITEM_EXIT_MS);
    },
    [items, removingIds],
  );
```

```ts
/* frontend/src/state/useBatchComposer.ts:237-261 — launchBatch, target (add cleanup) */
const launchBatch = useCallback(async (): Promise<string | null> => {
  if (!canLaunch) return null;
  setLaunching(true);
  setError(null);
  try {
    const requests: GenerateRequest[] = items.flatMap((item) => {
      const selectedModels = item.models.filter((model) => item.modelIds.includes(model.id));
      return buildGenerationQueue(selectedModels).map((model) => ({
        script: item.script,
        style: item.style,
        model_id: model.id,
        reference_image: item.referenceImage,
        denoise_strength: item.referenceImage ? item.denoiseStrength : undefined,
      }));
    });
    const { batch_id } = await api.postBatch(requests);
    Object.values(removeTimeouts.current).forEach((timeoutId) => window.clearTimeout(timeoutId));
    removeTimeouts.current = {};
    setRemovingIds(new Set());
    setItems([emptyItem()]);
    return batch_id;
  } catch (err) {
    setError(err as ApiError);
    return null;
  } finally {
    setLaunching(false);
  }
}, [items, canLaunch]);

return {
  items,
  questions,
  addItem,
  removeItem,
  removingIds,
  updateItem,
  /* … rest of the returned object unchanged … */
};
```

```tsx
/* frontend/src/pages/BatchComposerPage.tsx:22-40,72-74 — target */
export function BatchComposerPage({ onLaunched }: BatchComposerPageProps) {
  const {
    items,
    questions,
    addItem,
    removeItem,
    removingIds,
    updateItem,
    /* … rest unchanged … */
  } = useBatchComposer();

  /* … */

  return (
    <div className="batch-composer-page">
      {/* … */}
      <ul className="batch-composer-page__items">
        {items.map((item, index) => (
          <li
            className={`batch-composer-page__item${
              removingIds.has(item.id) ? " batch-composer-page__item--leaving" : ""
            }`}
            key={item.id}
          >
```

No `prefers-reduced-motion` block is needed: per `AUDIT.md` §6, reduced
motion means dropping *movement*, not opacity feedback. This plan's
`translateY(8px)` is a small (8px), brief motion on an occasional action —
consistent with how plans 001-003 already gate larger/more central
transforms but plan 004 (a small opacity-only fade) added no such block.
This one sits in between (it has a small transform); to stay consistent
with the codebase's existing pattern of gating any non-trivial `transform`
(plans 001-003), add the same style of block:

```css
@media (prefers-reduced-motion: reduce) {
  .batch-composer-page__item {
    transition: opacity 180ms ease-out;
  }

  @starting-style {
    .batch-composer-page__item {
      transform: none;
    }
  }

  .batch-composer-page__item--leaving {
    transform: none;
  }
}
```

## Repo conventions to follow

- Multi-property transitions are written as a comma-separated multi-line
  list, matching plans 001-003 (`frontend/src/index.css:110-113`,
  `:940-943`, `:853-855`).
- This is the third `@starting-style` usage in the file (after plans 003
  and 004) — same top-level at-rule form, placed immediately after the base
  rule it augments.
- `translateY(8px)` (settling upward into place) matches the direction
  established by plan 003's `.result-page__result`
  (`frontend/src/index.css:850-863`) — use the same positive value, not a
  new negative one, for a consistent "settle up" feel across the app's list
  entrances.
- The `removingIds` + `removeTimeouts` ref pattern mirrors plan 002's
  `lightboxVisible` + `lightboxCloseTimeout` ref in `ResultPage.tsx:61-104`
  exactly (state flips first to trigger the CSS exit transition, a
  `window.setTimeout` matching the CSS duration performs the actual removal,
  a cleanup effect clears any pending timeout on unmount) — same technique,
  generalized from a single boolean to a `Set<string>` because this is a
  list, not a single conditional element.
- `debounceTimers` in `BatchComposerPage.tsx:44` already uses the
  `useRef<Record<string, number>>({})` pattern for per-item timeouts —
  `removeTimeouts` in `useBatchComposer.ts` follows the same shape and
  naming style.

## Steps

1. In `frontend/src/state/useBatchComposer.ts`, add `useEffect` to the
   existing `react` import (already imports `useCallback`, `useEffect`,
   `useRef`, `useState` — `useEffect` is already there, no import change
   needed; only confirm it's present).
2. Add the `removingIds` state, `removeTimeouts` ref, and `ITEM_EXIT_MS`
   constant immediately after the existing `error` state
   (`frontend/src/state/useBatchComposer.ts:63`), as shown in Target.
3. Add the unmount-cleanup `useEffect` shown in Target, placed after the
   new state/ref declarations and before the existing
   `api.getQuestions()` effect (or immediately after it — either position
   is fine, just don't interleave it inside that effect's body).
4. Replace the `removeItem` callback (currently
   `frontend/src/state/useBatchComposer.ts:79-81`) with the target version
   shown above.
5. In `launchBatch` (currently `frontend/src/state/useBatchComposer.ts:237-261`),
   add the three cleanup lines (clear all pending timeouts, reset the
   `removeTimeouts` ref, reset `removingIds`) immediately after
   `const { batch_id } = await api.postBatch(requests);` and before
   `setItems([emptyItem()]);`.
6. Add `removingIds` to the hook's returned object (currently
   `frontend/src/state/useBatchComposer.ts:263-280`), placed after
   `removeItem` for readability.
7. In `frontend/src/pages/BatchComposerPage.tsx`, add `removingIds` to the
   destructured values from `useBatchComposer()` (currently lines 23-40).
8. Change the `<li>`'s `className` (currently
   `frontend/src/pages/BatchComposerPage.tsx:74`,
   `className="batch-composer-page__item"`) to the conditional string shown
   in Target, appending `" batch-composer-page__item--leaving"` when
   `removingIds.has(item.id)`.
9. In `frontend/src/index.css`, replace the `.batch-composer-page__item`
   rule (currently lines 1097-1105) with the target version: add
   `opacity: 1; transform: none;` and the two-property `transition`. Insert
   the `@starting-style` block immediately after it, then the
   `.batch-composer-page__item--leaving` rule, then the
   `@media (prefers-reduced-motion: reduce)` block, all as shown in Target,
   before `.batch-composer-page__item-header` (currently starting at line
   1107).

## Boundaries

- Do NOT change the `items.length > 1` guard that controls whether the
  remove **button** is rendered (`frontend/src/pages/BatchComposerPage.tsx:77`).
  This plan accepts one small, documented edge case: if a user has exactly
  2 items and removes one, the second item's remove button briefly remains
  visible (but inert — `removeItem`'s own `remainingCount` guard already
  makes a click on it a no-op) until the first item's ~220ms exit finishes
  and `items.length` actually drops to 1. Do not add extra logic to hide
  the button during this window — it is a sub-quarter-second edge case, not
  worth the added complexity for a LOW-severity polish item.
- Do NOT add height/`max-height` animation to `.batch-composer-page__item`
  or `.batch-composer-page__items` — animate `opacity`/`transform` only,
  per `AUDIT.md` §5. The vertical gap closing when an item leaves happens
  as an ordinary (unanimated) flex reflow once the item is actually removed
  from `items`, 220ms after the fade-out starts; this plan does not attempt
  to animate that reflow.
- Do NOT touch `debounceTimers` in `BatchComposerPage.tsx` or
  `resolveModelsForItem` in `useBatchComposer.ts` — unrelated to this
  plan; an item mid-removal simply stops receiving script updates
  harmlessly (its debounce timer firing after removal is a no-op `.map`
  over an array that no longer contains it).
- Do NOT change `addItem` — it already works correctly with the new
  `@starting-style` entrance with zero changes, since each new item is a
  genuine fresh mount.
- If any of the current-code excerpts above don't match what's on disk
  (drift since commit `e1ba50f`), STOP and report instead of improvising.

## Test fallout (found while implementing)

`frontend/tests/useBatchComposer.test.ts`'s `"adds and removes items, never
going below one"` test asserted the **old** synchronous contract
(`result.current.items` drops to length 1 immediately after calling
`removeItem`). That assertion is now legitimately false — removal is
deferred by `ITEM_EXIT_MS`. The test was updated (not reverted) to match
the new intentional contract: it now asserts the item is marked in
`removingIds` immediately, then uses `waitFor` (already the dominant async
pattern in this test file, e.g. lines 181/216/249) to assert `items` drops
to length 1 once the timeout fires, and that `removingIds` is empty
afterward. If executing this plan on a codebase where that test still
encodes the old synchronous behavior, update it the same way rather than
treating the resulting failure as a regression to work around.

## Verification

- **Mechanical**: from `frontend/`, run `npm run lint`, `npm run build`
  (`tsc -b` must accept `useState<Set<string>>(new Set())` and the
  `Record<string, number>` timeout ref), and `npm run test`. All three
  must stay clean.
- **Feel check**: start the dev server, open "Créer un batch":
  - Click "Ajouter un item" — confirm the new item fades in and rises
    ~8px into place, reading as a quick settle (~220ms), not sluggish.
  - With 3+ items, click the remove button on a middle item — confirm it
    fades out and sinks ~8px in place (not sliding away or collapsing
    height) before actually disappearing, and the items below it then
    shift up in one clean (unanimated) step once it's gone — no double
    animation, no layout jump before the fade finishes.
  - During that ~220ms fade-out, try clicking the same item's remove
    button again — confirm nothing happens (guarded by both
    `pointer-events: none` and the `removingIds.has(id)` check).
  - Reduce to exactly 2 items, click remove on one — confirm the other
    item's remove button is still visible during the ~220ms transition
    (documented, accepted edge case) but clicking it does nothing until
    the first item's removal finishes; after it finishes, the last
    remaining item has no remove button at all (existing `items.length > 1`
    guard).
  - Click "Lancer le batch" successfully (or simulate via a quick
    add/remove cycle right before launching) — confirm no stray console
    errors from a timeout firing after `items` was reset to a single
    empty item.
  - In DevTools Animations panel at 10% playback, confirm only `transform`
    and `opacity` animate on both add and remove — no layout-affecting
    properties.
  - Toggle `prefers-reduced-motion: reduce` — confirm items still fade in
    (opacity) but no longer rise/sink.
- **Done when**: adding an item fades/rises it into place, removing an
  item fades/sinks it out before the array actually shrinks, rapid or
  repeated remove clicks on the same item are safely ignored, launching a
  batch never leaves a dangling timeout, and reduced-motion users get
  opacity-only feedback.
