import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Who Pays Them? | Follow the Money on Your Ballot",
  description:
    "Enter your zip code. See your candidates. See who funds them. 100% public FEC data. Non-partisan. No spin.",
  openGraph: {
    title: "Who Pays Them?",
    description: "See who's funding your candidates. Just enter your zip code.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} antialiased`}>
        {/* Top red stripe */}
        <div className="h-1 bg-[#b22234]" />

        {children}

        {/* Footer */}
        <footer className="bg-[#0a1628] text-white/60 text-sm py-8 mt-12">
          <div className="max-w-4xl mx-auto px-4 text-center space-y-2">
            <p>
              Data from the{" "}
              <a
                href="https://www.fec.gov"
                className="text-white/80 underline hover:text-white"
                target="_blank"
                rel="noopener noreferrer"
              >
                Federal Election Commission
              </a>
              . Updated weekly.
            </p>
            <p>
              Non-partisan. No spin. Just public records.
            </p>
            <p className="text-white/40 text-xs mt-4">
              This tool presents publicly available campaign finance records. It does not endorse or oppose any candidate.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
