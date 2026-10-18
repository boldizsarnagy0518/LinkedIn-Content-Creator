import type { Metadata } from "next";
import { ServiceWorkerRegister } from "@/app/_components/service-worker-register";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "ContentOps", template: "%s | ContentOps" },
  description: "A durable, human-controlled editorial workflow for LinkedIn content.",
  applicationName: "ContentOps"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="hu">
      <body>{children}<ServiceWorkerRegister /></body>
    </html>
  );
}
