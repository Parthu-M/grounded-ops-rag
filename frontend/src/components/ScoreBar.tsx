interface ScoreBarProps {
  label: string;
  value: number;
  display?: string;
  tone?: "violet" | "green" | "amber";
}

export function ScoreBar({
  label,
  value,
  display,
  tone = "violet",
}: ScoreBarProps) {
  const percentage = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="score-row">
      <div className="score-row-label">
        <span>{label}</span>
        <strong>{display ?? value.toFixed(3)}</strong>
      </div>
      <div className="score-track" aria-label={`${label}: ${display ?? value}`}>
        <span
          className={`score-fill fill-${tone}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
