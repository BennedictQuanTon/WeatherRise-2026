import type { Metadata } from "next";
import "./globals.css";


export const metadata: Metadata = {
  title: "Weatherise",
  description:
    "AI-powered weather-risk analysis for tourism, construction, and agriculture in Vietnam. Powered by NVIDIA NIM.",
  keywords: ["weather", "risk", "tourism", "construction", "agriculture", "Vietnam", "AI", "NVIDIA"],
  icons: {
    icon: "/Weatherise_Logo.png",
    shortcut: "/Weatherise_Logo.png",
    apple: "/Weatherise_Logo.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="light">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
