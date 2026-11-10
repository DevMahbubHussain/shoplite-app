import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ShopLite — Cloud-Native E-Commerce',
  description: 'Resilient microservices order processing platform with full observability.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
