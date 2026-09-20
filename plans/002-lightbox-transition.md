# 002 — Animate the result lightbox open/close

- **Status**: DONE
- **Commit**: e1ba50f
- **Severity**: MEDIUM
- **Category**: Missed opportunities / Physicality & origin / Interruptibility
- **Estimated scope**: 2 files (`frontend/src/pages/ResultPage.tsx`, `frontend/src/index.css`), ~45 lines added/changed

## Problem

`ResultPage`'s lightbox — the full-screen zoom-in view for a generated image
— currently mounts and unmounts with a hard cut. Clicking a result image
sets `zoomedResult`, which conditionally renders the whole overlay tree
already at its final, fully-opaque, full-size state; clicking outside,
pressing the close button, or hitting Escape removes it from the DOM
instantly.

```tsx
/* frontend/src/pages/ResultPage.tsx:61-78 — current */
const [zoomedResult, setZoomedResult] = useState<GenerateResponse | null>(null);

useEffect(() => {
  if (loading) {
    setZoomedResult(null);
  }
}, [loading]);

useEffect(() => {
  if (!zoomedResult) return;
  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      setZoomedResult(null);
    }
  }
  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [zoomedResult]);
```

```tsx
/* frontend/src/pages/ResultPage.tsx:155-190 — current */
{zoomedResult && (
  <div
    className="lightbox"
    role="dialog"
    aria-modal="true"
    aria-label="Image en gros plan"
    onClick={() => setZoomedResult(null)}
  >
    <div className="lightbox__toolbar" onClick={(event) => event.stopPropagation()}>
      <a
        className="icon-button lightbox__download"
        href={zoomedResult.image_base64}
        download={downloadFileName(zoomedResult)}
        aria-label="Télécharger l'image"
        title="Télécharger l'image"
      >
        <DownloadIcon />
      </a>
      <button
        type="button"
        className="icon-button lightbox__close"
        onClick={() => setZoomedResult(null)}
        aria-label="Fermer"
        title="Fermer"
      >
        <CloseIcon />
      </button>
    </div>
    <img
      className="lightbox__image"
      src={zoomedResult.image_base64}
      alt={script}
      onClick={(event) => event.stopPropagation()}
    />
  </div>
)}
```

```css
/* frontend/src/index.css:918-944 — current */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem 1.5rem;
  z-index: 1000;
}

.lightbox__toolbar {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  gap: 0.5rem;
}

.lightbox__image {
  width: min(92vw, 1400px);
  height: min(88vh, 1000px);
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  cursor: default;
}
```

This is an occasional interaction (opened when the user wants to inspect one
result closely), so per `AUDIT.md` §1 it's eligible for standard animation,
and per §8 (Missed opportunities) a state that teleports in/out like this is
exactly the kind of jarring change worth smoothing.

Because the overlay is a plain React conditional (`{zoomedResult && (…)}`),
a CSS-only `@starting-style` fix would only cover the entrance — the moment
`setZoomedResult(null)` runs, React removes the element from the DOM on the
same tick, so there is no time for an exit transition to play. This plan
therefore introduces a small amount of state (a `visible` flag that lags the
open/close signal by one animation frame / one transition duration) so both
directions animate symmetrically, per `AUDIT.md` §8 ("Dismissable surfaces…
exit a different way than they entered → symmetric paths" — here, exactly
the same path, reversed).

## Target

Per `AUDIT.md` §2, modal/drawer duration budget is 200–500ms. Per §3, never
`scale(0)` — target `scale(0.9–0.97)`. This plan uses `scale(0.96)` for the
image (matches the earlier animation-opportunities report for this exact
element) and a plain opacity fade for the overlay backdrop. Per §2's decision
order, entering/exiting content should use a strong `ease-out` curve for the
deliberate part of the motion (the image's scale+opacity "pop"); the
backdrop's plain opacity fade can use the bare `ease-out` keyword, consistent
with how `frontend/src/index.css` already writes its transitions (see
`Repo conventions` below — this repo has no `--ease-*` custom properties and
plan 001 deliberately did not introduce one, so this plan also inlines the
raw cubic-bezier rather than defining a new token).

```tsx
/* frontend/src/pages/ResultPage.tsx:61-78 — target */
const [zoomedResult, setZoomedResult] = useState<GenerateResponse | null>(null);
const [lightboxVisible, setLightboxVisible] = useState(false);
const lightboxCloseTimeout = useRef<number | undefined>(undefined);

// Durée de sortie alignée sur la plus longue transition CSS de la lightbox
// (transform de .lightbox__image, 250ms) pour laisser l'animation finir
// avant le démontage réel.
const LIGHTBOX_EXIT_MS = 250;

function openLightbox(result: GenerateResponse) {
  window.clearTimeout(lightboxCloseTimeout.current);
  setZoomedResult(result);
  requestAnimationFrame(() => setLightboxVisible(true));
}

function closeLightbox() {
  setLightboxVisible(false);
  lightboxCloseTimeout.current = window.setTimeout(() => {
    setZoomedResult(null);
  }, LIGHTBOX_EXIT_MS);
}

useEffect(() => {
  if (loading) {
    window.clearTimeout(lightboxCloseTimeout.current);
    setLightboxVisible(false);
    setZoomedResult(null);
  }
}, [loading]);

useEffect(() => {
  if (!zoomedResult) return;
  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      closeLightbox();
    }
  }
  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [zoomedResult]);

useEffect(() => {
  return () => window.clearTimeout(lightboxCloseTimeout.current);
}, []);
```

```tsx
/* frontend/src/pages/ResultPage.tsx:155-190 — target */
{zoomedResult && (
  <div
    className={`lightbox${lightboxVisible ? " lightbox--visible" : ""}`}
    role="dialog"
    aria-modal="true"
    aria-label="Image en gros plan"
    onClick={closeLightbox}
  >
    <div className="lightbox__toolbar" onClick={(event) => event.stopPropagation()}>
      <a
        className="icon-button lightbox__download"
        href={zoomedResult.image_base64}
        download={downloadFileName(zoomedResult)}
        aria-label="Télécharger l'image"
        title="Télécharger l'image"
      >
        <DownloadIcon />
      </a>
      <button
        type="button"
        className="icon-button lightbox__close"
        onClick={closeLightbox}
        aria-label="Fermer"
        title="Fermer"
      >
        <CloseIcon />
      </button>
    </div>
    <img
      className="lightbox__image"
      src={zoomedResult.image_base64}
      alt={script}
      onClick={(event) => event.stopPropagation()}
    />
  </div>
)}
```

And the `setZoomedResult(result)` call in the results grid's zoom button
(`frontend/src/pages/ResultPage.tsx:117`, inside `onClick={() =>
setZoomedResult(result)}`) becomes `onClick={() => openLightbox(result)}`.

```css
/* frontend/src/index.css:918-944 — target */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem 1.5rem;
  z-index: 1000;
  opacity: 0;
  transition: opacity 200ms ease-out;
}

.lightbox--visible {
  opacity: 1;
}

.lightbox__toolbar {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  gap: 0.5rem;
}

.lightbox__image {
  width: min(92vw, 1400px);
  height: min(88vh, 1000px);
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  cursor: default;
  opacity: 0;
  transform: scale(0.96);
  transition:
    transform 250ms cubic-bezier(0.23, 1, 0.32, 1),
    opacity 200ms ease-out;
}

.lightbox--visible .lightbox__image {
  opacity: 1;
  transform: scale(1);
}

@media (prefers-reduced-motion: reduce) {
  .lightbox__image {
    transform: none;
    transition: opacity 200ms ease-out;
  }

  .lightbox--visible .lightbox__image {
    transform: none;
  }
}
```

## Repo conventions to follow

- Multi-property transitions are written as a comma-separated multi-line
  list, one property per line — see `frontend/src/index.css:132-138` (`.btn`)
  and the block plan 001 added at `frontend/src/index.css:110-113`
  (`button`'s `transform`/`border-color` transition). Match that exact
  formatting for `.lightbox__image`'s transition.
- This repo has no `--ease-*` design tokens. Plan 001 established the
  convention of using bare easing keywords/values inline rather than adding
  tokens; follow the same rule here — write `cubic-bezier(0.23, 1, 0.32, 1)`
  literally in the `.lightbox__image` transition, do not define a new custom
  property for it.
- `--visible`-style state-driven modifier classes already exist in this
  codebase, e.g. `.mode-selector__tile` / `.icon-button--active`
  (`frontend/src/index.css:759-762`) and
  `.batch-composer-page__mode-button--active`
  (`frontend/src/index.css:1046-1050`) — `.lightbox--visible` follows the
  same BEM-modifier naming pattern already used throughout this file.
- `frontend/src/index.css` now has one `@media (prefers-reduced-motion: reduce)`
  block, added by plan 001 directly under the `button` rules it modifies
  (`frontend/src/index.css:120-127`). Add this plan's reduced-motion block
  directly after `.lightbox--visible .lightbox__image`, in the same
  file-local placement style (next to the rules it overrides), not hoisted
  elsewhere.
- `ResultPage.tsx` already uses the `useEffect`/`useState` cleanup pattern
  for a window listener at lines 69-78 (the existing Escape-key effect) —
  mirror that same cleanup style (`return () => …`) for the new timeout
  cleanup effect.

## Steps

1. In `frontend/src/pages/ResultPage.tsx:1`, change the React import to add
   `useRef`: `import { useEffect, useRef, useState } from "react";`.
2. Replace the state/effects block at `frontend/src/pages/ResultPage.tsx:61-78`
   with the target block shown above: add `lightboxVisible` state and the
   `lightboxCloseTimeout` ref, add the `LIGHTBOX_EXIT_MS` constant, add the
   `openLightbox`/`closeLightbox` functions, update the `loading` effect to
   also reset `lightboxVisible` and clear the pending timeout (this is a
   forced close, not a user dismissal — no exit transition needed, reset
   both states synchronously), change the Escape handler to call
   `closeLightbox()` instead of `setZoomedResult(null)` directly, and add
   the new unmount-cleanup effect that clears `lightboxCloseTimeout`.
3. At `frontend/src/pages/ResultPage.tsx:117` (the zoom button inside the
   results grid, `onClick={() => setZoomedResult(result)}`), change it to
   `onClick={() => openLightbox(result)}`.
4. Replace the lightbox JSX block at `frontend/src/pages/ResultPage.tsx:155-190`
   with the target block above: the outer `<div>`'s `className` becomes the
   conditional `lightbox`/`lightbox lightbox--visible` string, its
   `onClick` becomes `closeLightbox` (drop the inline arrow, pass the
   function directly), and the close button's `onClick` also becomes
   `closeLightbox` directly. Leave the toolbar's `stopPropagation` handler,
   the download link, and the `<img>`'s `stopPropagation` handler
   unchanged.
5. In `frontend/src/index.css:918-944`, replace the `.lightbox` and
   `.lightbox__image` rules with the target CSS above: add `opacity: 0;`
   and `transition: opacity 200ms ease-out;` to `.lightbox`, add a new
   `.lightbox--visible { opacity: 1; }` rule right after it, add
   `opacity: 0; transform: scale(0.96);` plus the two-property transition
   to `.lightbox__image`, add a `.lightbox--visible .lightbox__image`
   rule that resets both to their settled values, and add the
   `@media (prefers-reduced-motion: reduce)` block immediately after that
   drops the scale transform but keeps the opacity fade. Leave
   `.lightbox__toolbar` untouched.

## Boundaries

- Do NOT change the lightbox's layout, sizing (`width`/`height`/`padding`),
  z-index, or the download/close icon buttons' own styling — this plan is
  entrance/exit motion only.
- Do NOT touch `.result-page__image-zoom-hint` or any other `result-page__*`
  rule — those are unrelated to the lightbox overlay itself.
- Do NOT introduce a new `--ease-*` custom property. Inline the cubic-bezier
  value as shown in Target, matching plan 001's precedent.
- Do NOT animate `width`/`height` on `.lightbox__image` — only `transform`
  and `opacity`, per `AUDIT.md` §5.
- Do NOT change `LIGHTBOX_EXIT_MS` from `250` without also updating the CSS
  transition durations to match — the JS timeout and the CSS transition
  duration for `.lightbox__image`'s `transform` must stay equal, or the
  element will either unmount mid-animation (visible cut) or sit invisible
  for longer than necessary before unmounting.
- If any of the three current-code excerpts above don't match what's on
  disk (drift since commit `e1ba50f`), STOP and report instead of
  improvising.

## Verification

- **Mechanical**: from `frontend/`, run `npm run lint`, `npm run build`, and
  `npm run test` (per `init/etat.md`: `cd frontend && npm run test && npm run build && npm run lint`).
  All three must stay clean. Pay particular attention to `npm run build`'s
  `tsc -b` step — `useRef<number | undefined>(undefined)` must typecheck
  cleanly against this project's TS config.
- **Feel check**: start the dev server, generate or open an existing result
  with at least one image (the Historique tab has past batch images if a
  fresh generation isn't convenient), then:
  - Click a result image to zoom in — confirm the dark backdrop fades in
    and the image scales up from ~96% to 100% while fading in, over what
    reads as a quick, responsive ~200-250ms (not sluggish, not instant).
  - Click the backdrop (not the image) to close — confirm the reverse:
    image shrinks slightly and fades while the backdrop fades out, and the
    lightbox is fully removed from the DOM (inspect via DevTools Elements
    panel) only after the animation visually finishes, not before.
  - Press Escape to close — same check as above.
  - Click rapidly to open, then immediately close before the entrance
    finishes — confirm no visual jump/flash and no leftover lightbox stuck
    half-visible (the CSS transition should retarget smoothly since this
    plan uses a transition, not a keyframe animation).
  - Trigger a new generation (or navigate away) while the lightbox is open
    — confirm it disappears immediately with no animation (this is the
    forced-close path via the `loading` effect, which is intentionally
    instant).
  - In DevTools, set the Animations panel playback to 10% and confirm only
    `opacity` and `transform` are animating — no layout shift.
  - Toggle `prefers-reduced-motion: reduce` in the Rendering panel, repeat
    the open/close check — confirm the image no longer scales but still
    fades in/out, and the backdrop still fades normally.
- **Done when**: opening the lightbox is a smooth fade+scale-in, closing
  (via backdrop click, close button, or Escape) is a symmetric fade+scale-out
  that finishes before the element unmounts, the forced-close-on-loading path
  remains instant, and reduced-motion users get opacity-only feedback.
