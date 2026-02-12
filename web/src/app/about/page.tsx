export default function AboutPage() {
  return (
    <main className="min-h-screen bg-[#f5f5f0]">
      {/* Header */}
      <div className="bg-[#0a1628] py-8 px-4">
        <div className="max-w-3xl mx-auto">
          <a href="/" className="text-white/60 hover:text-white text-sm">
            ← Back to search
          </a>
          <h1 className="text-3xl font-bold text-white mt-2">
            About This Tool
          </h1>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-10 space-y-8">
        {/* What is this */}
        <section className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-bold text-[#0a1628] mb-3">
            What is Who Pays Them?
          </h2>
          <p className="text-gray-700 leading-relaxed">
            Who Pays Them is a free, non-partisan tool that makes campaign
            finance data accessible to every voter. Enter your zip code and
            instantly see which candidates are running in your district and who
            is funding their campaigns — all sourced directly from federal
            public records.
          </p>
        </section>

        {/* Data source */}
        <section className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-bold text-[#0a1628] mb-3">
            Where Does the Data Come From?
          </h2>
          <p className="text-gray-700 leading-relaxed mb-3">
            All campaign finance data comes from the{" "}
            <a
              href="https://www.fec.gov"
              className="text-[#3b82f6] hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Federal Election Commission (FEC)
            </a>
            , the independent federal agency that regulates campaign finance in
            the United States. By law, all federal candidates must report their
            campaign contributions and expenditures to the FEC, and this data is
            public record.
          </p>
          <p className="text-gray-700 leading-relaxed">
            We use the{" "}
            <a
              href="https://api.open.fec.gov/developers/"
              className="text-[#3b82f6] hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              FEC&apos;s public API
            </a>{" "}
            to retrieve candidate information, campaign financial summaries, and
            itemized contributions (donations over $200). The zip code to
            congressional district mapping uses U.S. Census Bureau data.
          </p>
        </section>

        {/* How often updated */}
        <section className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-bold text-[#0a1628] mb-3">
            How Often Is It Updated?
          </h2>
          <p className="text-gray-700 leading-relaxed">
            The data refreshes automatically every week. Candidates file
            financial reports with the FEC on a regular schedule (quarterly, with
            additional pre-election reports), so the numbers you see here reflect
            the most recently filed reports.
          </p>
        </section>

        {/* What the numbers mean */}
        <section className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-bold text-[#0a1628] mb-3">
            What Do the Numbers Mean?
          </h2>
          <div className="space-y-3 text-gray-700 leading-relaxed">
            <p>
              <strong>Total Raised</strong> — The total amount of money a
              candidate&apos;s campaign committee has received during this
              election cycle.
            </p>
            <p>
              <strong>Individual</strong> — Contributions from individual people
              (both itemized donations over $200 and smaller unitemized
              donations).
            </p>
            <p>
              <strong>PAC</strong> — Contributions from Political Action
              Committees, which pool money from members to donate to campaigns.
            </p>
            <p>
              <strong>Party</strong> — Contributions from political party
              committees (DNC, RNC, state parties, etc.).
            </p>
            <p>
              <strong>Self-funded</strong> — Money the candidate contributed
              from their own personal funds.
            </p>
            <p>
              <strong>Top Donors</strong> — The organizations and individuals
              who have given the most to this candidate. Organization names
              represent contributions from employees of that organization, not
              the organization itself (corporations are prohibited from making
              direct contributions to federal candidates).
            </p>
          </div>
        </section>

        {/* Non-partisan commitment */}
        <section className="bg-white rounded-lg p-6 border-l-4 border-l-[#b22234]">
          <h2 className="text-xl font-bold text-[#0a1628] mb-3">
            Non-Partisan Commitment
          </h2>
          <p className="text-gray-700 leading-relaxed">
            This tool does not endorse or oppose any candidate, party, or
            political position. We present the same public data for every
            candidate equally, using the same methodology and the same data
            source. We do not editorialize, filter, or rank candidates. The
            data speaks for itself.
          </p>
        </section>

        {/* Disclaimer */}
        <section className="bg-gray-100 rounded-lg p-6 text-sm text-gray-600">
          <h2 className="font-bold text-gray-700 mb-2">Legal Disclaimer</h2>
          <p className="leading-relaxed">
            This tool presents publicly available campaign finance records filed
            with the Federal Election Commission. It is provided for
            informational purposes only. While we strive for accuracy, data may
            be delayed or incomplete due to FEC reporting schedules. For the most
            current and authoritative data, visit{" "}
            <a
              href="https://www.fec.gov"
              className="text-[#3b82f6] hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              FEC.gov
            </a>
            . The appearance of donor employer names does not imply that the
            employer endorsed or directed the contribution.
          </p>
        </section>

        {/* Back link */}
        <div className="text-center pt-4">
          <a
            href="/"
            className="inline-block px-6 py-3 bg-[#0a1628] text-white rounded-lg hover:bg-[#1a2744] transition-colors"
          >
            ← Look up your candidates
          </a>
        </div>
      </div>
    </main>
  );
}
