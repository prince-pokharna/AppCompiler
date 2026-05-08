import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AppCompiler — NL to App Generator",
  description:
    "Compile natural language descriptions into validated schemas and working Next.js applications. Powered by AI.",
  keywords: ["app generator", "AI", "natural language", "Next.js", "code generation"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="min-h-screen bg-[#0a0a0f] antialiased">
        {children}
      </body>
    </html>
  );
}
