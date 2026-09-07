"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Home, LoaderCircle, Plus, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, assetUrl } from "@/lib/api";
import type { Garment } from "@/lib/types";
import { ImageDropzone } from "./ImageDropzone";

const CATEGORIES = ["T-Shirt", "Polo", "Shirt", "Sweater", "Pants", "Shorts", "Sweatpants"];
const ROWS = [
  { label: "TEES", categories: ["T-Shirt"], defaultCategory: "T-Shirt" },
  { label: "POLOS", categories: ["Polo"], defaultCategory: "Polo" },
  { label: "SHIRTS", categories: ["Shirt", "Jacket"], defaultCategory: "Shirt" },
  { label: "SWEATSHIRTS", categories: ["Sweater", "Hoodie"], defaultCategory: "Sweater" },
  { label: "PANTS", categories: ["Pants", "Jeans"], defaultCategory: "Pants" },
  { label: "SHORTS", categories: ["Shorts"], defaultCategory: "Shorts" },
  { label: "SWEATPANTS", categories: ["Sweatpants"], defaultCategory: "Sweatpants" },
];

export function WardrobePageClient({ initialOpen = false }: { initialOpen?: boolean }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useQuery({ queryKey: ["user"], queryFn: api.getUser });
  const garments = useQuery({ queryKey: ["garments"], queryFn: api.getGarments });
  const [modalOpen, setModalOpen] = useState(initialOpen);
  const [initialCategory, setInitialCategory] = useState("T-Shirt");

  function openAdd(category: string) {
    setInitialCategory(category);
    setModalOpen(true);
  }

  function equip(garment: Garment) {
    window.localStorage.setItem("wardrobe-selected", garment.id);
    router.push("/");
  }

  if (user.isLoading || garments.isLoading) return <div className="sketch-loading"><span /></div>;

  return <main className="collection-page">
    <header className="collection-topbar">
      <Link href="/" className="collection-icon" aria-label="Home"><Home /></Link>
      <Link href="/profile" className="collection-name">{(user.data?.display_name ?? "CHU").toUpperCase()}</Link>
      <button className="collection-icon" aria-label="Add garment" onClick={() => openAdd("T-Shirt")}><Plus /></button>
    </header>

    <section className="collection-rows">
      {ROWS.map((row) => {
        const items = (garments.data ?? []).filter((garment) => row.categories.includes(garment.category));
        return <div className="collection-row" key={row.label}>
          <h1>{row.label}</h1>
          <div className="collection-strip">
            {items.map((garment) => <button key={garment.id} className="collection-card" onClick={() => equip(garment)} aria-label={garment.name}>
              <span className="collection-card-art">
                {garment.clean_front_url && <img src={assetUrl(garment.clean_front_url, garment.garment_version)!} alt="" />}
                <i className={`collection-state is-${garment.front_status}`} />
              </span>
              <span>{garment.category.toUpperCase()}</span>
            </button>)}
            <button className="collection-card is-add" onClick={() => openAdd(row.defaultCategory)} aria-label={`Add ${row.label.toLowerCase()}`}>
              <span className="collection-card-art"><Plus /></span>
              <span>{row.label}</span>
            </button>
          </div>
        </div>;
      })}
    </section>

    {modalOpen && <GarmentModal initialCategory={initialCategory} onClose={() => setModalOpen(false)} onCreated={() => {
      void queryClient.invalidateQueries({ queryKey: ["garments"] });
      setModalOpen(false);
      router.replace("/wardrobe");
    }} />}
  </main>;
}

function GarmentModal({ initialCategory, onClose, onCreated }: { initialCategory: string; onClose: () => void; onCreated: () => void }) {
  const [front, setFront] = useState<File | null>(null);
  const [back, setBack] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!front) {
      setError("Front image is required.");
      return;
    }
    const data = new FormData(event.currentTarget);
    const brand = String(data.get("brand") ?? "").trim();
    const color = String(data.get("color") ?? "").trim();
    const category = String(data.get("category") ?? initialCategory);
    data.set("name", [color, brand, category].filter(Boolean).join(" ") || category);
    data.set("front", front);
    if (back) data.set("back", back);
    else data.delete("back");
    setSaving(true);
    setError(null);
    try {
      await api.createGarment(data);
      onCreated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed.");
      setSaving(false);
    }
  }

  return <div className="collection-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && !saving && onClose()}>
    <form className="collection-modal" onSubmit={submit}>
      <button type="button" className="collection-modal-close" onClick={onClose} aria-label="Close" disabled={saving}><X /></button>
      <div className="collection-upload-grid">
        <ImageDropzone label="FRONT · REQUIRED" hint="Full garment" value={front} onChange={setFront} />
        <ImageDropzone label="BACK · OPTIONAL" hint="Add later if needed" value={back} onChange={setBack} />
      </div>
      <div className="collection-fields">
        <label><span>BRAND · OPTIONAL</span><input className="field" name="brand" maxLength={120} /></label>
        <label><span>CATEGORY</span><select className="field" name="category" defaultValue={initialCategory}>{CATEGORIES.map((category) => <option key={category} value={category}>{category === "T-Shirt" ? "Tee" : category === "Sweater" ? "Sweatshirt" : category}</option>)}</select></label>
        <label><span>COLOR · OPTIONAL</span><input className="field" name="color" maxLength={80} /></label>
      </div>
      {error && <p className="collection-error" role="alert">{error}</p>}
      <button className="collection-submit" disabled={saving}>{saving ? <LoaderCircle className="animate-spin" /> : <Plus />}{saving ? "PROCESSING" : "ADD"}</button>
    </form>
  </div>;
}
