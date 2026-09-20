import type { ActivityRingData } from "./ActivityRing";
import { ActivityRing } from "./ActivityRing";

const DEFAULT_RINGS: ActivityRingData[] = [
  {
    label: "Move",
    value: 85,
    color: "#ff2d55",
    colorEnd: "#ff6b8b",
    size: 180,
    current: 479,
    target: 800,
    unit: "cal",
  },
  {
    label: "Exercise",
    value: 60,
    color: "#a3f900",
    colorEnd: "#c5ff4d",
    size: 140,
    current: 24,
    target: 30,
    unit: "min",
  },
  {
    label: "Stand",
    value: 30,
    color: "#04c7dd",
    colorEnd: "#4ddfed",
    size: 100,
    current: 6,
    target: 12,
    unit: "hr",
  },
];

interface AppleActivityCardProps {
  title?: string;
  rings?: ActivityRingData[];
}

// Reproduction en CSS pur (pas de Tailwind/framer-motion dans ce projet) du
// composant registry shadcn @kokonutui/apple-activity-card — anneaux
// d'activité empilés façon Apple Watch, réutilisable avec d'autres données
// (voir HistoryPage : progression d'un batch).
export function AppleActivityCard({
  title = "Activity Rings",
  rings = DEFAULT_RINGS,
}: AppleActivityCardProps) {
  const containerSize = rings[0]?.size ?? 0;

  return (
    <div className="activity-card">
      <h2 className="activity-card__title">{title}</h2>
      <div className="activity-card__body">
        <div
          className="activity-card__rings"
          style={{ width: containerSize, height: containerSize }}
        >
          {rings.map((ring, index) => (
            <div
              key={ring.label}
              className="activity-card__ring-layer"
              style={{ transitionDelay: `${index * 150}ms` }}
            >
              <ActivityRing ring={ring} delayMs={index * 150} />
            </div>
          ))}
        </div>

        <ul className="activity-card__stats">
          {rings.map((ring) => (
            <li key={ring.label} className="activity-card__stat">
              <span className="activity-card__stat-label">{ring.label}</span>
              <span className="activity-card__stat-value" style={{ color: ring.color }}>
                {ring.current !== undefined && ring.target !== undefined
                  ? `${ring.current}/${ring.target}`
                  : `${Math.round(ring.value)}%`}
                {ring.unit && <span className="activity-card__stat-unit">{ring.unit}</span>}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
