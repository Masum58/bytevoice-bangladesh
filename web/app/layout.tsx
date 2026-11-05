import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ByteVoice Bangladesh — AI Voice Receptionist for Dhaka Dental Care",
  description: "Natural Bangla AI Voice Receptionist for dental clinics and hospitals in Bangladesh by StrategyByte.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="bn" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-emerald-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
