import type { Metadata } from "next";
import { Providers } from "@/components/Providers";
import "./globals.css";
export const metadata: Metadata = { title:"Digital Wardrobe", description:"A private, local-first 2D virtual wardrobe powered by CatVTON." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Providers>{children}</Providers></body></html>;
}
