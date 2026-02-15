export default function AboutPage() {
  return (
    <main className="min-h-screen bg-[#f5f5f0]">
      {/* Header */}
      <div className="bg-[#0a1628] py-8 px-4">
        <div className="max-w-3xl mx-auto">
          <a href="/" className="text-white/60 hover:text-white text-sm">
            &larr; Back to search
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
            is funding their campaigns &mdash; sourced directly from federal and
            state public records.
          </p>
        </section>

        {/* Data sources */}
        <section className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-bold text-[#0a1628] mb-3">
            Where Does the Data Come From?
          </h2>
          <div className="space-y-3 text-gray-700 leading-relaxed">
            <p>
              <strong>Federal candidates</strong> (U.S. Senate and House) &mdash;
              All data comes from the{" "}
              <a
                href="https://www.fec.gov"
                className="text-[#3b82f6] hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Federal Election Commission (FEC)
              </a>
              , the independent federal agency that regulates campaign finance.
              By law, all federal candidates must report their contributions and
              expenditures to the FEC, and this data is public record. We use
              the{" "}
              <a
                href="https://api.open.fec.gov/developers/"
                className="text-[#3b82f6] hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                FEC&apos;s public API
              </a>{" "}
              for candidate information, financial summaries, itemized
              contributions (donations over $200), and independent expenditures.
            </p>
            <p>
              <strong>Governor candidates</strong> &mdash; Candidate lists come
              from{" "}
              <a
                href="https://ballotpedia.org"
                className="text-[#3b82f6] hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Ballotpedia
              </a>
              . Campaign finance data comes from multiple state-level sources:{" "}
              <a
                href="https://www.transparencyusa.org"
                className="text-[#3b82f6] hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                TransparencyUSA
              </a>{" "}
              (20 states),{" "}
              <a
                href="https://www.followthemoney.org"
                className="text-[#3b82f6] hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                FollowTheMoney.org
              </a>{" "}
              (National Institute on Money in Politics), and direct state
              disclosure agency data for select states.
            </p>
            <p>
              <strong>Zip code mapping</strong> &mdash; The zip code to
              congressional district mapping uses U.S. Census Bureau ZCTA data.
            </p>
          </div>
        </section>

        {/* How often updated */}
        <section className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-bold text-[#0a1628] mb-3">
            How Often Is It Updated?
          </h2>
          <p className="text-gray-700 leading-relaxed">
            The data refreshes automatically every week. Candidates file
            financial reports on a regular schedule (quarterly, with additional
            pre-election reports), so the numbers you see here reflect the most
            recently filed reports. State-level data may lag behind federal data
            depending on when each state processes filings.
          </p>
        </section>

        {/* What the numbers mean */}
        <section className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-bold text-[#0a1628] mb-3">
            What Do the Numbers Mean?
          </h2>
          <div className="space-y-3 text-gray-700 leading-relaxed">
            <p>
              <strong>Total Raised</strong> &mdash; The total amount of money a
              candidate&apos;s campaign committee has received during this
              election cycle.
            </p>
            <p>
              <strong>Total Spent</strong> &mdash; The total amount the campaign
              has disbursed (spent) during this election cycle, including
              advertising, staff, travel, and other expenses.
            </p>
            <p>
              <strong>Individual</strong> &mdash; Contributions from individual
              people (both itemized donations over $200 and smaller unitemized
              donations).
            </p>
            <p>
              <strong>PAC</strong> &mdash; Contributions from Political Action
              Committees, which pool money from members to donate to campaigns.
            </p>
            <p>
              <strong>Party</strong> &mdash; Contributions from political party
              committees (DNC, RNC, state parties, etc.).
            </p>
            <p>
              <strong>Self-funded</strong> &mdash; Money the candidate
              contributed from their own personal funds.
            </p>
            <p>
              <strong>Top Donors</strong> &mdash; The organizations and
              individuals who have given the most to this candidate. Organization
              names represent contributions from employees of that organization,
              not the organization itself (corporations are prohibited from
              making direct contributions to federal candidates).
            </p>
            <p>
              <strong>Outside Spending</strong> &mdash; Money spent by
              independent groups (Super PACs, 501(c)(4) organizations, etc.) to
              support or oppose a candidate. These groups cannot coordinate with
              the candidate&apos;s campaign but can spend unlimited amounts.
              &quot;Supporting&quot; means spending that advocates for the
              candidate; &quot;opposing&quot; means spending that advocates
              against them.
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
            sources. We do not editorialize, filter, or rank candidates. The
            data speaks for itself.
          </p>
        </section>

        {/* Disclaimer */}
        <section className="bg-gray-100 rounded-lg p-6 text-sm text-gray-600">
          <h2 className="font-bold text-gray-700 mb-2">Legal Disclaimer</h2>
          <p className="leading-relaxed">
            This tool presents publicly available campaign finance records from
            the Federal Election Commission, state campaign finance disclosure
            agencies, TransparencyUSA, and FollowTheMoney.org. It is provided
            for informational purposes only. While we strive for accuracy, data
            may be delayed or incomplete due to reporting schedules. For the most
            current and authoritative federal data, visit{" "}
            <a
              href="https://www.fec.gov"
              className="text-[#3b82f6] hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              FEC.gov
            </a>
            . For state-level data, check your state&apos;s campaign finance
            disclosure agency. The appearance of donor employer names does not
            imply that the employer endorsed or directed the contribution.
          </p>
        </section>

        {/* Back link */}
        <div className="text-center pt-4">
          <a
            href="/"
            className="inline-block px-6 py-3 bg-[#0a1628] text-white rounded-lg hover:bg-[#1a2744] transition-colors"
          >
            &larr; Look up your candidates
          </a>
        </div>
      </div>
    </main>
  );
}
