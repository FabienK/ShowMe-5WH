# 003 — Reveal each generated result on arrival

- **Status**: DONE
- **Commit**: e1ba50f
- **Severity**: LOW
- **Category**: Missed opportunities (delight) / Physicality & origin
- **Estimated scope**: 1 file, ~20 lines added (`frontend/src/index.css`)

## Problem

`ResultPage` renders one `.result-page__result` card per finished image
inside `.result-page__results`. Today the card has no styling of its own
beyond layout — it snaps into the grid at full opacity the instant it
mounts, with no acknowledgment that the user just waited (per
`init/etat.md`) **~4 min 15s for an SDXL image, up to 40 min for Flux
Kontext**.

```tsx
/* frontend/src/pages/ResultPage.tsx:115-164 — current, unchanged by this plan */
{results.length > 0 && (
  <div className="result-page__results">
    {results.map((result, index) => {
      /* … */
      return (
        <div
          className="result-page__result"
          key={`${result.preset_used.model_id}-${index}`}
        >
          {results.length > 1 && (
            <h3 className="result-page__result-title">…</h3>
          )}
          <div className="result-page__image-wrap">…</div>
        </div>
      );
    })}
  </div>
)}
```

```css
/* frontend/src/index.css:861-865 — current */
.result-page__results {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}
```

No `.result-page__result` rule exists at all in `frontend/src/index.css` —
the card is unstyled beyond what it inherits as a grid item.

Confirmed in `frontend/src/state/useGenerationFlow.ts:172` —
`setResults((prev) => [...prev, generated]);` — results are appended **one
at a time**, in a sequential loop, as each model finishes (ComfyUI processes
one job at a time; see `init/etat.md`'s hardware-constraints section). This
matters for the fix: each `.result-page__result` is a genuinely new DOM node
with a new `key` when it mounts (React never remounts the earlier cards), so
a plain per-element mount transition is enough — **no artificial stagger is
needed**, because completions are already naturally spaced out by real
generation time (this deliberately departs from the earlier
find-animation-opportunities report, which speculated a stagger for
"multiple models finishing" — that scenario doesn't happen for this
component; results never arrive simultaneously here).

Per `AUDIT.md` §1/§8, this is a rare, high-emotion moment (the payoff of a
multi-minute wait) — exactly where the delight budget is meant to be spent,
and exactly the kind of teleporting state change §8 flags as worth
smoothing.

## Target

Per `AUDIT.md` §3, never `scale(0)` — target range is `scale(0.9–0.97)`;
this plan uses `0.97` (subtle, matches the earlier report). Per §4, entry
without JS should use `@starting-style` — no JS state is needed here (unlike
the lightbox in plan 002) because this is a pure mount with no corresponding
unmount to animate. This repo's CSS has no nesting anywhere, so `@starting-style`
is added as its own top-level at-rule rather than nested inside the selector,
matching the flat-rule style already used throughout `index.css`.

```css
/* frontend/src/index.css:861-865 — target (new rule inserted after .result-page__results) */
.result-page__results {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.result-page__result {
  opacity: 1;
  transform: none;
  transition:
    transform 350ms cubic-bezier(0.23, 1, 0.32, 1),
    opacity 300ms ease-out;
}

@starting-style {
  .result-page__result {
    opacity: 0;
    transform: translateY(8px) scale(0.97);
  }
}

@media (prefers-reduced-motion: reduce) {
  .result-page__result {
    transition: opacity 300ms ease-out;
  }

  @starting-style {
    .result-page__result {
      transform: none;
    }
  }
}
```

## Repo conventions to follow

- Multi-property transitions are written as a comma-separated multi-line
  list, one property per line, matching `frontend/src/index.css:110-113`
  (`button`, from plan 001) and `frontend/src/index.css:940-943`
  (`.lightbox__image`, from plan 002).
- The strong `ease-out` curve `cubic-bezier(0.23, 1, 0.32, 1)` is already
  used inline (not as a token) at `frontend/src/index.css:941` for the
  lightbox image's entrance — reuse the exact same literal value here for
  consistency across the codebase's "deliberate pop" moments. This repo
  still has no `--ease-*` custom properties; do not add one (same boundary
  as plans 001 and 002).
- This is the first `@starting-style` usage in the file — place both the
  base rule and its `@starting-style` counterpart immediately after
  `.result-page__results` (the parent grid), before `.result-page__image-wrap`,
  so the reveal styling for a result card lives next to the grid it belongs
  to.
- `frontend/src/index.css` now has two `@media (prefers-reduced-motion: reduce)`
  blocks (from plans 001 and 002), each placed directly after the rule(s)
  it overrides rather than hoisted to one shared location — follow that same
  local-placement convention for this third one.

## Steps

1. In `frontend/src/index.css`, immediately after the `.result-page__results`
   rule (currently lines 861-865) and before `.result-page__image-wrap`
   (currently line 867), insert the new `.result-page__result` rule and its
   `@starting-style` block, exactly as shown in Target.
2. Immediately after that, insert the `@media (prefers-reduced-motion: reduce)`
   block shown in Target, which keeps the opacity fade but drops the
   `translateY`/`scale` entrance.
3. Do not touch `frontend/src/pages/ResultPage.tsx` — no JSX or state
   changes are needed for this plan; the existing `key={...}` per result
   already gives each card a fresh mount to animate from.

## Boundaries

- Do NOT add a stagger delay (`transition-delay`, inline `--index` custom
  property, etc.) — confirmed unnecessary per the Problem section; results
  arrive one at a time in this flow, never as a simultaneous batch.
- Do NOT touch `.result-page__result-title`, `.result-page__image-wrap`,
  `.result-page__image-button`, `.result-page__image-zoom-hint`, or
  `.result-page__download` — the whole card (title + image together)
  reveals as one unit via the parent `.result-page__result` rule; do not
  add separate per-child transitions.
- Do NOT modify `HistoryPage.tsx` or its thumbnail rendering — that is a
  separate component (batch results, not this single/multi-model generation
  flow) and was explicitly deferred as its own candidate (#4 in the earlier
  find-animation-opportunities report), not part of this plan.
- Do NOT add a JS-driven `data-mounted` fallback for `@starting-style`. If
  a browser doesn't support it, the card simply appears without the
  transition (no error, no broken layout) — acceptable progressive
  enhancement for this single-user local app; do not add extra state to
  work around it.
- If the current-code excerpts above don't match what's on disk (drift
  since commit `e1ba50f`), STOP and report instead of improvising.

## Verification

- **Mechanical**: from `frontend/`, run `npm run lint`, `npm run build`, and
  `npm run test`. All three must stay clean — this plan touches CSS only,
  so no TypeScript surface changes, but confirm no regressions anyway.
- **Feel check**: this needs at least one real result to land in
  `ResultPage`, which requires ComfyUI running locally (per `init/etat.md`)
  — if that isn't available, replicate the exact CSS in a static HTML file
  with a button that appends a new `.result-page__result` div to a
  `.result-page__results` grid on click, served over `http://localhost`
  (not `file://`, which the in-app browser preview renders as a static,
  non-interactive snapshot), and check:
  - Each new card fades in and rises ~8px while scaling from 97% to 100%,
    reading as a quick, satisfying "arrival" — not sluggish (it's ~350ms,
    the upper end of what still feels responsive for a rare/delight moment).
  - Cards already in the grid do NOT replay the animation when a new card
    is appended next to them (confirms React isn't remounting existing
    `key`s).
  - In DevTools Animations panel at 10% playback, confirm only `transform`
    and `opacity` animate — no layout shift, no reflow of sibling cards.
  - Toggle `prefers-reduced-motion: reduce` in the Rendering panel — confirm
    the card still fades in but no longer rises/scales.
  - Resize to a narrow (mobile) viewport and confirm the grid's
    `auto-fit`/`minmax(220px, 1fr)` reflow still behaves normally with the
    new transition in place (no interaction between the reveal and the
    responsive grid columns).
- **Done when**: every newly-arrived result card fades and rises into place
  once, existing cards are undisturbed by later arrivals, and reduced-motion
  users get an opacity-only fade.
