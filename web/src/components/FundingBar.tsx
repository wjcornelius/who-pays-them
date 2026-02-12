interface FundingBreakdown {
  individual: number;
  pac: number;
  party: number;
  self: number;
  other: number;
}

export default function FundingBar({
  breakdown,
}: {
  breakdown: FundingBreakdown;
}) {
  const segments = [
    { key: "individual", label: "Individual", pct: breakdown.individual, color: "bg-blue-500" },
    { key: "pac", label: "PAC", pct: breakdown.pac, color: "bg-amber-500" },
    { key: "party", label: "Party", pct: breakdown.party, color: "bg-purple-500" },
    { key: "self", label: "Self-funded", pct: breakdown.self, color: "bg-green-500" },
    { key: "other", label: "Other", pct: breakdown.other, color: "bg-gray-400" },
  ].filter((s) => s.pct > 0);

  if (segments.length === 0) {
    return <div className="text-sm text-gray-400 italic">No funding data available</div>;
  }

  return (
    <div>
      {/* Bar */}
      <div className="flex h-3 rounded-full overflow-hidden bg-gray-200">
        {segments.map((s) => (
          <div
            key={s.key}
            className={`${s.color} transition-all`}
            style={{ width: `${s.pct}%` }}
            title={`${s.label}: ${s.pct}%`}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-600">
        {segments.map((s) => (
          <span key={s.key} className="flex items-center gap-1">
            <span className={`inline-block w-2 h-2 rounded-full ${s.color}`} />
            {s.label} {s.pct}%
          </span>
        ))}
      </div>
    </div>
  );
}
