# Animation plans

| # | Title | Severity | Status |
| --- | --- | --- | --- |
| [001](001-button-press-feedback.md) | Add press feedback to the base `button` element | HIGH | DONE |
| [002](002-lightbox-transition.md) | Animate the result lightbox open/close | MEDIUM | DONE |
| [003](003-result-reveal.md) | Reveal each generated result on arrival | LOW | DONE |
| [004](004-history-thumbnail-reveal.md) | Fade in history thumbnails as they resolve | LOW | DONE |
| [005](005-batch-item-add-remove.md) | Animate batch item add/remove | LOW | DONE |
| [006](006-error-banner-reveal.md) | Fade in the error banner on appearance | LOW | DONE |

## Execution order

No dependencies between 001-006 — different files/rules, different
concerns. Run any standalone: `improve-animations execute 006-error-banner-reveal.md`,
or hand `plans/006-error-banner-reveal.md` to any agent directly. This is
the last of the 6 opportunities from the original find-animation-opportunities
report.

## Notes

`.btn`-classed buttons (HomePage only: "Générer" CTAs, cancel/confirm on the
image-reference panel) and `.mode-selector__tile` are explicitly out of scope
for 001 — they already have their own hover-driven `transform`
(`translateY`), and giving them press feedback too needs a follow-up plan
that resolves the `:hover`/`:active` specificity interaction rather than
bolting a scale onto the base `button` rule.
