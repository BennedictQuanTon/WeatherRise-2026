import type { Metadata } from "next";
import "./globals.css";


export const metadata: Metadata = {
  title: "Weatherise — Weather-Risk Intelligence",
  description:
    "AI-powered weather-risk analysis for tourism, construction, and agriculture in Vietnam. Powered by NVIDIA NIM.",
  keywords: ["weather", "risk", "tourism", "construction", "agriculture", "Vietnam", "AI", "NVIDIA"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
