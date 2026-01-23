import type { Metadata } from 'next';
import { Quando, Inter } from 'next/font/google';
import './globals.css';
import { AppProviders } from './providers/AppProviders';
import { Web3MoneyBackground } from './components/Web3MoneyBackground';

const quando = Quando({ 
  subsets: ['latin'],
  weight: '400',
  variable: '--font-quando',
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'UClaim - Fast claims. Safe payouts.',
  description: 'Submit claims, get AI-assisted evaluation, and settle payouts in USDC with an audit-ready evidence trail.',
  keywords: ['insurance', 'claims', 'AI', 'blockchain', 'USDC', 'Arc'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${quando.variable} ${inter.variable} font-inter min-h-screen bg-background text-text-primary antialiased`}>
        <Web3MoneyBackground />
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
