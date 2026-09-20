import type { MouseEvent } from "react";

// Met à jour --spot-x/--spot-y sur l'élément survolé, consommées par le halo
// radial CSS (voir .card::before, .mode-selector__featured::before, etc.)
export function trackSpotlight(event: MouseEvent<HTMLElement>) {
  const target = event.currentTarget;
  const rect = target.getBoundingClientRect();
  target.style.setProperty("--spot-x", `${event.clientX - rect.left}px`);
  target.style.setProperty("--spot-y", `${event.clientY - rect.top}px`);
}
