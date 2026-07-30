import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

// Inter é a fonte definida no PRD: legibilidade em telas densas de formulário.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Pacta",
  description: "Gestão do ciclo de vida de contratos",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">{children}</body>
    </html>
  );
}
