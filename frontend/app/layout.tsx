import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'ClaimLedger - AI-Powered Insurance Claims',
  description: 'Submit insurance claims, get AI evaluation, and receive USDC settlements on Arc blockchain.',
  keywords: ['insurance', 'claims', 'AI', 'blockchain', 'USDC', 'Arc'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen bg-[#0f172a] text-white antialiased`}>
        <div className="relative min-h-screen">
          {/* Background gradient blobs */}
          <div className="fixed inset-0 overflow-hidden pointer-events-none">
            <div className="blob blob-1" />
            <div className="blob blob-2" />
            <div className="blob blob-3" />
          </div>
          
          {/* Main content */}
          <div className="relative z-10">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
