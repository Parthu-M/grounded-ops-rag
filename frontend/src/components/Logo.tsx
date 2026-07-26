export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand-lockup" role="img" aria-label="Grounded Ops">
      <div className="brand-mark" aria-hidden="true">
        <span className="brand-mark-corner" />
        <span className="brand-mark-square" />
      </div>
      {!compact && (
        <div>
          <div className="brand-name">Grounded</div>
          <div className="brand-suffix">OPS</div>
        </div>
      )}
    </div>
  );
}
