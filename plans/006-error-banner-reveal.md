# 006 — Fade in the error banner on appearance

- **Status**: DONE
- **Commit**: e1ba50f
- **Severity**: LOW
- **Category**: Missed opportunities (preventing a jarring change)
- **Estimated scope**: 1 file, ~14 lines added (`frontend/src/index.css`)

## Problem

`ErrorBanner` is mounted conditionally in three places, always as
`{condition && <ErrorBanner .../>}` — a genuine fresh mount each time an
error appears, never an update to an already-rendered element:

```tsx
/* frontend/src/components/ErrorBanner.tsx — current, unchanged by this plan */
export function ErrorBanner({ error }: ErrorBannerProps) {
  return (
    <div className="error-banner" role="alert">
      <strong>Erreur.</strong> {error.detail}
    </div>
  );
}
```

```tsx
/* frontend/src/App.tsx:51 */
{flow.step !== "result" && flow.error && <ErrorBanner error={flow.error} />}
```

```tsx
/* frontend/src/pages/BatchComposerPage.tsx:71 */
{error && <ErrorBanner error={error} />}
```

```tsx
/* frontend/src/pages/ResultPage.tsx:113 */
{!loading && error && <ErrorBanner error={error} />}
```

```css
/* frontend/src/index.css:463-468 — current */
.error-banner {
  background: var(--error-bg);
  color: var(--error-text);
  border-radius: var(--radius-sm);
  padding: 0.75rem 1rem;
}
```

Today the banner snaps into view instantly the moment an API call fails.
Per `AUDIT.md` §8, this is a state change that teleports and would benefit
from a brief transition; per §1 it's occasional (only on actual errors).

Confirmed in `frontend/src/state/useGenerationFlow.ts` and
`useBatchComposer.ts`: `setError(...)` is always cleared to `null` at the
*start* of the next action (e.g. `useGenerationFlow.ts:76,92,112,126,151,204,219,240`
all call `setError(null)` before making a new request), and neither
`ErrorBanner` nor any caller exposes a dismiss/close control. The banner
always disappears silently as a side effect of the user's next action, not
something they watch closely the way they watch the lightbox close (plan
002) — so, unlike plan 002, **no exit animation is needed here**: a plain
`@starting-style` entrance (same zero-JS mechanism as plans 003/004) is
enough, since every appearance is a genuine fresh mount.

## Target

Per the earlier find-animation-opportunities report for this exact element
and per `AUDIT.md` §2 (small popover/alert budget, 125-250ms) and §3 (never
`scale(0)`; this plan uses no scale at all — a small vertical drop is
enough for an alert banner, consistent with the report's suggested value):

```css
/* frontend/src/index.css:463-468 — target */
.error-banner {
  background: var(--error-bg);
  color: var(--error-text);
  border-radius: var(--radius-sm);
  padding: 0.75rem 1rem;
  opacity: 1;
  transform: none;
  transition:
    transform 200ms ease-out,
    opacity 200ms ease-out;
}

@starting-style {
  .error-banner {
    opacity: 0;
    transform: translateY(-4px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .error-banner {
    transition: opacity 200ms ease-out;
  }

  @starting-style {
    .error-banner {
      transform: none;
    }
  }
}
```

Note the direction: `translateY(-4px)` is **negative** (the banner drops
down into place from slightly above its resting position), unlike plans
003/005's `translateY(8px)` (cards/list items settling *upward* into
place). This is a deliberate, not accidental, difference — an alert banner
sitting at the top of its container reads naturally as "dropping in" from
above (the conventional notification/alert idiom), whereas a card populating
a grid or a list item settling into a vertical stack reads naturally as
rising into place. Do not "fix" this to match the other plans' direction.

## Repo conventions to follow

- Multi-property transitions are written as a comma-separated multi-line
  list, matching plans 001-003/005 (e.g. `frontend/src/index.css:110-113`).
- This is the fourth `@starting-style` usage in the file (after plans 003,
  004, 005) — same top-level at-rule form, placed immediately after the
  base rule it augments.
- `@media (prefers-reduced-motion: reduce)` blocks are placed directly
  after the rule(s) they override, not hoisted elsewhere — same local
  placement as plans 001, 003 (skipped for 004, whose transition was
  already opacity-only) and 005.

## Steps

1. In `frontend/src/index.css`, in the `.error-banner` rule (currently
   lines 463-468), add `opacity: 1; transform: none;` and the two-property
   `transition` shown in Target.
2. Immediately after that rule, insert the `@starting-style` block shown in
   Target.
3. Immediately after that, insert the `@media (prefers-reduced-motion: reduce)`
   block shown in Target.
4. Do not touch `frontend/src/components/ErrorBanner.tsx`,
   `frontend/src/App.tsx`, `frontend/src/pages/BatchComposerPage.tsx`, or
   `frontend/src/pages/ResultPage.tsx` — no JSX or state changes are
   needed; every existing conditional render already produces a fresh
   mount when an error appears.

## Boundaries

- Do NOT add an exit/dismiss animation or a close button — confirmed
  unnecessary per the Problem section (errors clear silently as a side
  effect of the user's next action; there is no user-watched close
  interaction to animate, unlike plan 002's lightbox).
- Do NOT add scale — a small vertical drop + fade is enough for this
  element; do not over-animate an error message.
- Do NOT change `translateY(-4px)` to a positive value to match plans
  003/005 — see Target for why the direction is intentionally different
  here.
- If the current-code excerpts above don't match what's on disk (drift
  since commit `e1ba50f`), STOP and report instead of improvising.

## Verification

- **Mechanical**: from `frontend/`, run `npm run lint`, `npm run build`,
  and `npm run test`. All three must stay clean — CSS-only change, no
  TypeScript surface affected.
- **Feel check**: the easiest reliable way to trigger a real error without
  a running backend is the "Générateur" flow with the backend/ComfyUI not
  running (an existing, already-common local state per `init/etat.md`) —
  or the "Créer un batch" flow's launch button with the backend down.
  Trigger any request that fails and confirm:
  - The banner fades in and drops ~4px into place over ~200ms — subtle,
    not bouncy, reading as "an alert appeared" rather than a celebration.
  - Trigger a second, different error right after the first is showing in
    the same spot (e.g. two failed actions in a row) — confirm the second
    mount (new element, since the first one unmounted when `error` was
    cleared to `null` before the retry) also fades in cleanly, no stacking
    or double-render artifacts.
  - In DevTools Animations panel at 10% playback, confirm only `transform`
    and `opacity` animate — no layout shift in the surrounding content.
  - Toggle `prefers-reduced-motion: reduce` — confirm the banner still
    fades in but no longer drops.
- **Done when**: every appearance of the error banner (in the Générateur
  flow, the batch composer, and the result page) fades and drops in once
  on mount, with no change to how or when it disappears.
