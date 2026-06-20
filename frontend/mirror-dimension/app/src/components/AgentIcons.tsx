interface IconProps {
  color: string;
  size?: number;
}

export function PrismIcon({ color, size = 48 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <polygon
        points="24,4 44,14 44,34 24,44 4,34 4,14"
        stroke={color}
        strokeWidth="1.5"
        fill="none"
      />
      <line x1="24" y1="4" x2="24" y2="24" stroke={color} strokeWidth="1" opacity="0.5" />
      <line x1="4" y1="14" x2="24" y2="24" stroke={color} strokeWidth="1" opacity="0.5" />
      <line x1="44" y1="14" x2="24" y2="24" stroke={color} strokeWidth="1" opacity="0.5" />
    </svg>
  );
}

export function OracleIcon({ color, size = 48 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <path
        d="M24 8 C12 8, 4 20, 4 24 C4 28, 12 40, 24 40 C36 40, 44 28, 44 24 C44 20, 36 8, 24 8Z"
        stroke={color}
        strokeWidth="1.5"
        fill="none"
      />
      <circle cx="24" cy="24" r="8" stroke={color} strokeWidth="1.5" fill="none" />
      <circle cx="24" cy="24" r="3" fill={color} opacity="0.6" />
    </svg>
  );
}

export function RadarIcon({ color, size = 48 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <path d="M24 4 A20 20 0 0 1 44 24" stroke={color} strokeWidth="1.5" fill="none" />
      <path d="M24 12 A12 12 0 0 1 36 24" stroke={color} strokeWidth="1.5" fill="none" />
      <path d="M24 20 A4 4 0 0 1 28 24" stroke={color} strokeWidth="1.5" fill="none" />
      <line x1="24" y1="24" x2="24" y2="4" stroke={color} strokeWidth="1" opacity="0.5">
        <animateTransform attributeName="transform" type="rotate" from="0 24 24" to="360 24 24" dur="4s" repeatCount="indefinite" />
      </line>
    </svg>
  );
}

export function CortexIcon({ color, size = 48 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <circle cx="24" cy="24" r="6" stroke={color} strokeWidth="1.5" fill="none" />
      <circle cx="12" cy="12" r="3" stroke={color} strokeWidth="1" fill="none" />
      <circle cx="36" cy="12" r="3" stroke={color} strokeWidth="1" fill="none" />
      <circle cx="12" cy="36" r="3" stroke={color} strokeWidth="1" fill="none" />
      <circle cx="36" cy="36" r="3" stroke={color} strokeWidth="1" fill="none" />
      <line x1="24" y1="18" x2="12" y2="15" stroke={color} strokeWidth="1" opacity="0.5" />
      <line x1="24" y1="18" x2="36" y2="15" stroke={color} strokeWidth="1" opacity="0.5" />
      <line x1="24" y1="30" x2="12" y2="33" stroke={color} strokeWidth="1" opacity="0.5" />
      <line x1="24" y1="30" x2="36" y2="33" stroke={color} strokeWidth="1" opacity="0.5" />
    </svg>
  );
}

export function NexusIcon({ color, size = 48 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <circle cx="18" cy="24" r="12" stroke={color} strokeWidth="1.5" fill="none" />
      <circle cx="30" cy="24" r="12" stroke={color} strokeWidth="1.5" fill="none" />
    </svg>
  );
}
