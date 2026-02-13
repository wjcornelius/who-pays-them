import FundingBar from "./FundingBar";

interface Donor {
  name: string;
  amount: number;
  type: string;
  description?: string;
}

interface Candidate {
  name: string;
  party: string;
  party_full: string;
  incumbent: boolean;
  total_raised: number;
  total_raised_display: string;
  funding_breakdown: {
    individual: number;
    pac: number;
    party: number;
    self: number;
    other: number;
  };
  top_donors: Donor[];
  fec_id: string;
  fec_url: string;
  tusa_url?: string;
  state_disclosure_url?: string;
  office?: string;
}

function partyColor(party: string): string {
  switch (party) {
    case "D": return "bg-blue-600";
    case "R": return "bg-red-600";
    case "L": return "bg-yellow-500";
    case "G": return "bg-green-600";
    default: return "bg-gray-500";
  }
}

function partyBorder(party: string): string {
  switch (party) {
    case "D": return "border-l-blue-600";
    case "R": return "border-l-red-600";
    case "L": return "border-l-yellow-500";
    case "G": return "border-l-green-600";
    default: return "border-l-gray-500";
  }
}

function formatDollar(amount: number): string {
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `$${Math.round(amount / 1_000)}K`;
  return `$${amount.toLocaleString()}`;
}

export default function CandidateCard({ candidate }: { candidate: Candidate }) {
  const isGovernor = candidate.office === "Governor";
  const hasFinanceData = candidate.total_raised > 0 || candidate.top_donors.length > 0;

  return (
    <div className={`bg-white rounded-lg shadow-sm border-l-4 ${partyBorder(candidate.party)} p-5 hover:shadow-md transition-shadow`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold text-[#0a1628]">{candidate.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className={`${partyColor(candidate.party)} text-white text-xs font-bold px-2 py-0.5 rounded`}>
              {candidate.party}
            </span>
            {candidate.incumbent && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">Incumbent</span>
            )}
          </div>
        </div>
        {hasFinanceData && (
          <div className="text-right">
            <div className="text-2xl font-bold text-[#0a1628]">{candidate.total_raised_display}</div>
            <div className="text-xs text-gray-500">total raised</div>
          </div>
        )}
      </div>

      {/* Funding breakdown bar (only for federal candidates with FEC data) */}
      {hasFinanceData && !isGovernor && (
        <div className="mb-4">
          <FundingBar breakdown={candidate.funding_breakdown} />
        </div>
      )}

      {/* Note for governor candidates without finance data */}
      {isGovernor && !hasFinanceData && (
        <div className="text-sm text-gray-500 italic">
          Finance data not yet available for this candidate.
          {candidate.state_disclosure_url && (
            <> Check <a href={candidate.state_disclosure_url} target="_blank" rel="noopener noreferrer" className="text-[#3b82f6] hover:underline not-italic">state disclosure records</a>.</>
          )}
        </div>
      )}

      {/* Top donors */}
      {candidate.top_donors.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Top Donors</h4>
          <div className="space-y-1.5">
            {candidate.top_donors.slice(0, 5).map((donor, i) => (
              <div key={i} className="flex justify-between items-center text-sm">
                <span className="text-gray-700 truncate mr-2">
                  {i + 1}. {donor.name}
                  {donor.type === "pac" && (
                    <span className="ml-1 text-[10px] font-bold text-orange-600 bg-orange-50 px-1 py-0.5 rounded">PAC</span>
                  )}
                </span>
                <span className="font-medium text-[#0a1628] whitespace-nowrap">{formatDollar(donor.amount)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Source link - only show when we have actual data to back it up */}
      {hasFinanceData && (candidate.fec_url || candidate.tusa_url) && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          {candidate.fec_url && (
            <a href={candidate.fec_url} target="_blank" rel="noopener noreferrer" className="text-xs text-[#3b82f6] hover:underline">
              View full FEC record →
            </a>
          )}
          {candidate.tusa_url && !candidate.fec_url && (
            <a href={candidate.tusa_url} target="_blank" rel="noopener noreferrer" className="text-xs text-[#3b82f6] hover:underline">
              View full finance record →
            </a>
          )}
        </div>
      )}
    </div>
  );
}
