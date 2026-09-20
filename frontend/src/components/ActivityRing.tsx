import { useEffect, useId, useState } from "react";

export interface ActivityRingData {
  label: string;
  value: number;
  color: string;
  colorEnd: string;
  size: number;
  current?: number;
  target?: number;
  unit?: string;
}

interface ActivityRingProps {
  ring: ActivityRingData;
  strokeWidth?: number;
  delayMs?: number;
  centerLabel?: string;
}

// Anneau de progression façon Apple Watch — remplissage animé au montage
// (délai optionnel pour empiler plusieurs anneaux en cascade, voir
// AppleActivityCard), réutilisé tel quel pour une progression isolée
// (QuestionPage, Historique). `centerLabel` optionnel : un court texte
// centré dans l'anneau (ex. un décompte), à la place du remplissage seul.
export function ActivityRing({ ring, strokeWidth = 14, delayMs = 0, centerLabel }: ActivityRingProps) {
  const [filled, setFilled] = useState(false);
  const gradientId = `activity-ring-gradient-${useId()}`;

  useEffect(() => {
    const frame = requestAnimationFrame(() => setFilled(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const radius = (ring.size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = filled ? ((100 - ring.value) / 100) * circumference : circumference;
  const accessibleLabel =
    centerLabel !== undefined
      ? `${ring.label}: ${centerLabel} remaining`
      : `${ring.label}: ${Math.round(ring.value)}%`;

  return (
    <svg
      className="activity-ring"
      width={ring.size}
      height={ring.size}
      viewBox={`0 0 ${ring.size} ${ring.size}`}
      role="img"
      aria-label={accessibleLabel}
    >
      <title>{accessibleLabel}</title>
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={ring.color} />
          <stop offset="100%" stopColor={ring.colorEnd} />
        </linearGradient>
      </defs>
      <circle
        className="activity-ring__track"
        cx={ring.size / 2}
        cy={ring.size / 2}
        r={radius}
        strokeWidth={strokeWidth}
        fill="none"
      />
      <circle
        className="activity-ring__fill"
        cx={ring.size / 2}
        cy={ring.size / 2}
        r={radius}
        strokeWidth={strokeWidth}
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${ring.size / 2} ${ring.size / 2})`}
        style={{ transitionDelay: `${delayMs}ms` }}
      />
      {centerLabel !== undefined && (
        <text
          className="activity-ring__center-label"
          x={ring.size / 2}
          y={ring.size / 2}
          textAnchor="middle"
          dominantBaseline="central"
          style={{ fontSize: ring.size * 0.42 }}
        >
          {centerLabel}
        </text>
      )}
    </svg>
  );
}
