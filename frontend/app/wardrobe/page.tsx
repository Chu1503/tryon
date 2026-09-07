import { WardrobePageClient } from "@/components/WardrobePageClient";

export default async function WardrobePage({ searchParams }: { searchParams: Promise<{ add?: string }> }) {
  const query = await searchParams;
  return <WardrobePageClient initialOpen={query.add === "1"} />;
}
