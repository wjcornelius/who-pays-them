"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import CandidateCard from "@/components/CandidateCard";

interface DistrictInfo {
  state: string;
  state_name: string;
  districts: string[];
}

interface Race {
  race_key: string;
  label: string;
  state: string;
  office: string;
  candidates: Array<{
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
    top_donors: Array<{
      name: string;
      amount: number;
      type: string;
      description?: string;
    }>;
    fec_id: string;
    fec_url: string;
  }>;
}

export default function ResultsPage() {
  const params = useParams();
  const zip = params.zip as string;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [districtInfo, setDistrictInfo] = useState<DistrictInfo | null>(null);
  const [races, setRaces] = useState<Race[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        // Load district mapping
        const distResp = await fetch("/data/districts.json");
        if (!distResp.ok) {
          setError("Data not yet available. The pipeline needs to run first.");
          setLoading(false);
          return;
        }
        const districts = await distResp.json();

        const info = districts[zip];
        if (!info) {
          setError(`No congressional district found for zip code ${zip}. Please check and try again.`);
          setLoading(false);
          return;
        }
        setDistrictInfo(info);

        // Load candidates
        const candResp = await fetch("/data/candidates.json");
        if (!candResp.ok) {
          setError("Candidate data not yet available.");
          setLoading(false);
          return;
        }
        const allRaces = await candResp.json();

        // Find matching races for this zip's state/districts
        const matchingRaces: Race[] = [];
        const state = info.state;

        // Senate race
        const senateKey = `${state}-senate`;
        if (allRaces[senateKey]) {
          matchingRaces.push(allRaces[senateKey]);
        }

        // House race(s)
        for (const dist of info.districts) {
          const houseKey = `${state}-house-${dist}`;
          if (allRaces[houseKey]) {
            matchingRaces.push(allRaces[houseKey]);
          }
        }

        setRaces(matchingRaces);
        setLoading(false);
      } catch {
        setError("Error loading data. Please try again.");
        setLoading(false);
      }
    }

    loadData();
  }, [zip]);

  if (loading) {
    return (
      <main className="min-h-screen bg-[#f5f5f0]">
        <div className="bg-[#0a1628] py-8 px-4">
          <div className="max-w-4xl mx-auto">
            <a href="/" className="text-white/60 hover:text-white text-sm">← Back</a>
            <h1 className="text-3xl font-bold text-white mt-2">Loading...</h1>
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-[#f5f5f0]">
        <div className="bg-[#0a1628] py-8 px-4">
          <div className="max-w-4xl mx-auto">
            <a href="/" className="text-white/60 hover:text-white text-sm">← Back</a>
            <h1 className="text-3xl font-bold text-white mt-2">Zip Code: {zip}</h1>
          </div>
        </div>
        <div className="max-w-4xl mx-auto px-4 py-12">
          <div className="bg-white rounded-lg p-8 text-center">
            <p className="text-lg text-gray-600">{error}</p>
            <a href="/" className="inline-block mt-6 px-6 py-3 bg-[#0a1628] text-white rounded-lg hover:bg-[#1a2744]">
              Try another zip code
            </a>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f5f5f0]">
      {/* Header */}
      <div className="bg-[#0a1628] py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <a href="/" className="text-white/60 hover:text-white text-sm">← Back to search</a>
          <h1 className="text-3xl font-bold text-white mt-2">
            YOUR RACES — {districtInfo?.state_name || districtInfo?.state}
          </h1>
          <p className="text-white/60 mt-1">Zip code: {zip}</p>
        </div>
      </div>

      {/* Races */}
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-10">
        {races.length === 0 ? (
          <div className="bg-white rounded-lg p-8 text-center">
            <p className="text-lg text-gray-600">
              No 2026 races found for this location yet. Data updates weekly as candidates file with the FEC.
            </p>
          </div>
        ) : (
          races.map((race) => (
            <section key={race.race_key}>
              {/* Race header with red stripe */}
              <div className="flex items-center gap-3 mb-4">
                <div className="w-1 h-8 bg-[#b22234] rounded-full" />
                <h2 className="text-xl font-bold text-[#0a1628]">{race.label}</h2>
              </div>

              {/* Candidate cards */}
              <div className="grid gap-4 md:grid-cols-2">
                {race.candidates.map((candidate) => (
                  <CandidateCard key={candidate.fec_id || candidate.name} candidate={candidate} />
                ))}
              </div>
            </section>
          ))
        )}

        {/* Data source attribution */}
        <div className="text-center text-sm text-gray-500 pt-8 border-t border-gray-200">
          <p>
            All data from{" "}
            <a href="https://www.fec.gov" className="text-[#3b82f6] hover:underline" target="_blank" rel="noopener noreferrer">
              FEC.gov
            </a>
            . Updated weekly. •{" "}
            <a href="/about" className="text-[#3b82f6] hover:underline">About this tool</a>
          </p>
        </div>
      </div>
    </main>
  );
}
