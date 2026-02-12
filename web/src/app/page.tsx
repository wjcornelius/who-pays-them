"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const [zip, setZip] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cleaned = zip.replace(/\D/g, "").slice(0, 5);
    if (cleaned.length !== 5) {
      setError("Please enter a 5-digit zip code");
      return;
    }
    setError("");
    router.push(`/results/${cleaned}`);
  }

  return (
    <main>
      {/* Hero section - navy with stars */}
      <div className="bg-[#0a1628] stars-bg min-h-[70vh] flex flex-col items-center justify-center px-4 text-center">
        {/* Flag-inspired accent stripes */}
        <div className="flex gap-1 mb-8">
          <div className="w-8 h-1 bg-[#b22234] rounded-full" />
          <div className="w-8 h-1 bg-white rounded-full" />
          <div className="w-8 h-1 bg-[#b22234] rounded-full" />
        </div>

        <h1 className="text-5xl md:text-7xl font-bold text-white tracking-tight mb-4">
          WHO PAYS THEM<span className="text-[#b22234]">?</span>
        </h1>

        <p className="text-xl md:text-2xl text-white/80 mb-12 max-w-xl">
          See who&apos;s funding your candidates.
          <br />
          Just enter your zip code.
        </p>

        {/* Zip code input */}
        <form onSubmit={handleSubmit} className="w-full max-w-md">
          <div className="flex gap-3">
            <input
              type="text"
              inputMode="numeric"
              maxLength={5}
              placeholder="Enter zip code"
              value={zip}
              onChange={(e) => {
                setZip(e.target.value.replace(/\D/g, "").slice(0, 5));
                setError("");
              }}
              className="flex-1 px-6 py-4 text-xl text-center rounded-lg bg-white text-[#0a1628] font-bold tracking-widest placeholder:font-normal placeholder:tracking-normal placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#b22234]"
              autoFocus
            />
            <button
              type="submit"
              className="px-8 py-4 text-lg font-bold rounded-lg bg-[#b22234] text-white hover:bg-[#d4344a] transition-colors focus:outline-none focus:ring-2 focus:ring-white"
            >
              LOOK IT UP
            </button>
          </div>
          {error && (
            <p className="mt-3 text-[#d4344a] font-medium">{error}</p>
          )}
        </form>

        {/* Trust signals */}
        <div className="flex flex-wrap justify-center gap-6 mt-12 text-white/50 text-sm">
          <span>100% public FEC data</span>
          <span className="hidden sm:inline">|</span>
          <span>Non-partisan</span>
          <span className="hidden sm:inline">|</span>
          <span>No spin</span>
          <span className="hidden sm:inline">|</span>
          <span>Updated weekly</span>
        </div>
      </div>

      {/* How it works section */}
      <div className="max-w-4xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-[#0a1628] text-center mb-10">
          How It Works
        </h2>
        <div className="grid md:grid-cols-3 gap-8 text-center">
          <div>
            <div className="text-4xl mb-3">1</div>
            <h3 className="font-bold text-lg mb-2">Enter Your Zip</h3>
            <p className="text-gray-600">
              We find your congressional district and the races on your ballot.
            </p>
          </div>
          <div>
            <div className="text-4xl mb-3">2</div>
            <h3 className="font-bold text-lg mb-2">See Your Candidates</h3>
            <p className="text-gray-600">
              Every candidate running in your district — incumbents and challengers.
            </p>
          </div>
          <div>
            <div className="text-4xl mb-3">3</div>
            <h3 className="font-bold text-lg mb-2">Follow the Money</h3>
            <p className="text-gray-600">
              Top donors, total raised, and where the money comes from. Every dollar linked to FEC records.
            </p>
          </div>
        </div>

        <div className="text-center mt-12">
          <a href="/about" className="text-[#3b82f6] hover:underline">
            Learn more about our data and methodology →
          </a>
        </div>
      </div>
    </main>
  );
}
