"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Grid2X2, LoaderCircle, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api, assetUrl } from "@/lib/api";
import type { Garment, View } from "@/lib/types";

type CategoryKey = "tees" | "polos" | "shirts" | "sweatshirts" | "pants" | "shorts" | "sweatpants";

type CategoryDefinition = {
  key: CategoryKey;
  label: string;
  side: "left" | "right";
  categories: string[];
};

const CATEGORIES: CategoryDefinition[] = [
  { key: "pants", label: "PANTS", side: "left", categories: ["Pants", "Jeans"] },
  { key: "shorts", label: "SHORTS", side: "left", categories: ["Shorts"] },
  { key: "sweatpants", label: "SWEATPANTS", side: "left", categories: ["Sweatpants"] },
  { key: "tees", label: "TEES", side: "right", categories: ["T-Shirt"] },
  { key: "polos", label: "POLOS", side: "right", categories: ["Polo"] },
  { key: "shirts", label: "SHIRTS", side: "right", categories: ["Shirt", "Jacket"] },
  { key: "sweatshirts", label: "SWEATSHIRTS", side: "right", categories: ["Sweater", "Hoodie"] },
];
const DISPLAY_ASSET_REVISION = "trim-2";

function CategoryGlyph({ type }: { type: CategoryKey }) {
  if (type === "pants" || type === "sweatpants" || type === "shorts") {
    const hem = type === "shorts" ? 49 : 68;
    return <svg viewBox="0 0 80 80" aria-hidden="true"><path d={`M23 12h34l-2 27 8 ${hem - 39}H45l-5-${hem - 43}-5 ${hem - 43}H17l8-${hem - 39}-2-27Z`} /><path d="M24 20h32M40 13v30" /></svg>;
  }
  if (type === "polos") {
    return <svg viewBox="0 0 80 80" aria-hidden="true"><path d="m24 14 16 7 16-7 16 13-10 14-7-5v32H25V36l-7 5L8 27l16-13Z" /><path d="m31 17 9 16 9-16M40 33v17" /></svg>;
  }
  if (type === "shirts") {
    return <svg viewBox="0 0 80 80" aria-hidden="true"><path d="m25 13 15 7 15-7 17 17-11 12-6-6v32H25V36l-6 6L8 30l17-17Z" /><path d="M40 21v47M31 16l9 9 9-9M34 42h12" /></svg>;
  }
  if (type === "sweatshirts") {
    return <svg viewBox="0 0 80 80" aria-hidden="true"><path d="M28 15c2-8 22-8 24 0l17 15-10 13-6-6v31H27V37l-6 6-10-13 17-15Z" /><path d="M29 15c6 8 16 8 22 0M31 55h18" /></svg>;
  }
  return <svg viewBox="0 0 80 80" aria-hidden="true"><path d="m24 14 16 8 16-8 17 14-11 14-7-6v32H25V36l-7 6L7 28l17-14Z" /><path d="M30 17c2 8 18 8 20 0" /></svg>;
}

function viewField(garment: Garment, view: View, field: "status" | "progress" | "cutout") {
  if (field === "cutout") return garment[`tryon_${view}_cutout_url` as keyof Garment] as string | null;
  return garment[`${view}_${field}` as keyof Garment] as Garment["front_status"] | number;
}

export function WardrobeClient() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeCategory, setActiveCategory] = useState<CategoryKey | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState<View>("front");
  const userQuery = useQuery({ queryKey: ["user"], queryFn: api.getUser });
  const garmentsQuery = useQuery({
    queryKey: ["garments"],
    queryFn: api.getGarments,
    refetchInterval: (query) => query.state.data?.some((item) => item.front_status === "processing" || item.back_status === "processing") ? 900 : false,
  });
  const garments = garmentsQuery.data ?? [];

  useEffect(() => {
    if (userQuery.data && !userQuery.data.is_complete) router.replace("/profile");
  }, [router, userQuery.data]);

  useEffect(() => {
    const remembered = window.localStorage.getItem("wardrobe-selected");
    if (remembered && garments.some((item) => item.id === remembered)) setSelectedId(remembered);
  }, [garments]);

  const selected = useMemo(() => garments.find((item) => item.id === selectedId) ?? null, [garments, selectedId]);
  const activeDefinition = CATEGORIES.find((item) => item.key === activeCategory) ?? null;
  const choices = useMemo(
    () => activeDefinition ? garments.filter((item) => activeDefinition.categories.includes(item.category)) : [],
    [activeDefinition, garments],
  );

  const generate = useMutation({
    mutationFn: ({ id, target }: { id: string; target: View }) => api.generate(id, target),
    onSuccess: (result) => queryClient.setQueryData<Garment[]>(["garments"], (current) => current?.map((item) => item.id === result.garment.id ? result.garment : item)),
  });

  const generationLocked = Boolean(
    generate.isPending || (selected && viewField(selected, view, "status") === "processing"),
  );

  function chooseGarment(garment: Garment) {
    setSelectedId(garment.id);
    window.localStorage.setItem("wardrobe-selected", garment.id);
    const status = viewField(garment, view, "status");
    const hasView = view === "front" ? garment.clean_front_url : garment.clean_back_url;
    if (status !== "ready" && status !== "processing" && hasView) generate.mutate({ id: garment.id, target: view });
  }

  if (userQuery.isLoading || garmentsQuery.isLoading || !userQuery.data) return <div className="sketch-loading"><span /></div>;
  if (userQuery.error || garmentsQuery.error) return <div className="sketch-loading is-error"><span /></div>;

  const bodyCutout = assetUrl(
    view === "front" ? userQuery.data.body_front_cutout_url : userQuery.data.body_back_cutout_url,
    `${userQuery.data.body_reference_version}-${DISPLAY_ASSET_REVISION}`,
  );
  const selectedCutout = selected && viewField(selected, view, "status") === "ready"
    ? assetUrl(viewField(selected, view, "cutout") as string | null, `${selected.garment_version}-${selected.updated_at}-${DISPLAY_ASSET_REVISION}`)
    : null;
  const playerImage = selectedCutout ?? bodyCutout;

  return <main className={`sketch-home ${activeDefinition ? `is-choosing panel-${activeDefinition.side}` : ""} ${generationLocked ? "is-generation-locked" : ""}`}>
    <div className="sketch-world-grid" />
    <Link href="/profile" aria-disabled={generationLocked} onClick={(event) => generationLocked && event.preventDefault()} className="sketch-player-name">{userQuery.data.display_name.toUpperCase()}</Link>
    <Link href="/wardrobe" aria-disabled={generationLocked} onClick={(event) => generationLocked && event.preventDefault()} className="sketch-wardrobe-link" aria-label="Open wardrobe"><Grid2X2 /></Link>

    {activeDefinition && <button
      className="sketch-panel-dismiss"
      aria-label={generationLocked ? "Generation in progress" : "Close clothing panel"}
      onClick={() => !generationLocked && setActiveCategory(null)}
    />}

    <div className="sketch-category-side is-left">
      {CATEGORIES.filter((item) => item.side === "left").map((item) => <CategoryBlock key={item.key} definition={item} garments={garments} active={activeCategory === item.key} onClick={() => setActiveCategory(activeCategory === item.key ? null : item.key)} />)}
    </div>

    <div className="sketch-player">
      {playerImage && <img src={playerImage} alt={userQuery.data.display_name} />}
      {selected && viewField(selected, view, "status") === "processing" && <span className="sketch-player-progress"><i style={{ width: `${viewField(selected, view, "progress")}%` }} /></span>}
    </div>

    <div className="sketch-category-side is-right">
      {CATEGORIES.filter((item) => item.side === "right").map((item) => <CategoryBlock key={item.key} definition={item} garments={garments} active={activeCategory === item.key} onClick={() => setActiveCategory(activeCategory === item.key ? null : item.key)} />)}
    </div>

    {activeDefinition && <aside className={`sketch-choices is-${activeDefinition.side}`} aria-label={`${activeDefinition.label} choices`}>
      {choices.map((garment) => <button key={garment.id} disabled={generationLocked} className={`sketch-choice ${selectedId === garment.id ? "is-selected" : ""}`} aria-label={garment.name} onClick={() => chooseGarment(garment)}>
        {garment.clean_front_url ? <img src={assetUrl(garment.clean_front_url, garment.garment_version)!} alt="" /> : <CategoryGlyph type={activeDefinition.key} />}
        {garment.front_status === "processing" && <span><i style={{ width: `${garment.front_progress}%` }} /></span>}
      </button>)}
      <Link href="/wardrobe?add=1" aria-disabled={generationLocked} onClick={(event) => generationLocked && event.preventDefault()} className="sketch-choice is-add" aria-label="Add garment"><Plus /></Link>
      {generationLocked && <div className="sketch-generation-warning" role="status" aria-live="polite">
        <LoaderCircle />
        <span>GENERATION IN PROGRESS</span>
        <i><b style={{ width: `${selected ? viewField(selected, view, "progress") : 1}%` }} /></i>
      </div>}
    </aside>}
  </main>;
}

function CategoryBlock({ definition, garments, active, onClick }: { definition: CategoryDefinition; garments: Garment[]; active: boolean; onClick: () => void }) {
  const preview = garments.find((item) => definition.categories.includes(item.category) && item.clean_front_url);
  return <button className={`sketch-category ${active ? "is-active" : ""}`} onClick={onClick} aria-pressed={active}>
    <span className="sketch-category-block">{preview?.clean_front_url ? <img src={assetUrl(preview.clean_front_url, preview.garment_version)!} alt="" /> : <CategoryGlyph type={definition.key} />}</span>
    <span className="sketch-category-label">{definition.label}</span>
  </button>;
}
