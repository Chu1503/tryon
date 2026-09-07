"use client";

import { ArrowLeft, ArrowRight, Check, LoaderCircle, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, assetUrl } from "@/lib/api";
import type { Garment, View } from "@/lib/types";
import { ImageDropzone } from "./ImageDropzone";
import { SiteHeader } from "./SiteHeader";

const CATEGORIES = ["T-Shirt", "Shirt", "Sweater", "Hoodie", "Jacket", "Pants", "Jeans", "Shorts", "Other"];

export function AddGarmentClient() {
  const router = useRouter();
  const [front, setFront] = useState<File | null>(null);
  const [back, setBack] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Garment | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!front) {
      setError("Add a front garment photo.");
      return;
    }
    setSaving(true);
    setError(null);
    const data = new FormData(event.currentTarget);
    data.set("front", front);
    if (back) data.set("back", back);
    else data.delete("back");
    try {
      setCreated(await api.createGarment(data));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The garment could not be processed.");
    } finally {
      setSaving(false);
    }
  }

  async function generateFront() {
    if (!created) return;
    setSaving(true);
    try {
      await api.generate(created.id, "front");
      router.push("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Generation could not start.");
      setSaving(false);
    }
  }

  if (created) {
    const processedViews: View[] = created.clean_back_url ? ["front", "back"] : ["front"];
    return <>
      <SiteHeader compact />
      <main className="mx-auto max-w-[1180px] px-5 py-12 md:px-10 md:py-16">
        <div className="text-center">
          <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-[#e2e9de] text-[#496044]"><Check size={18} /></span>
          <p className="eyebrow mt-5">Garment processed</p>
          <h1 className="mt-3 font-display text-5xl">Clean and ready.</h1>
          <p className="mx-auto mt-4 max-w-lg text-sm leading-6 text-muted">Every supplied view was cleaned and centered on a consistent transparent canvas.</p>
        </div>
        <div className="mx-auto mt-10 grid max-w-4xl gap-5 md:grid-cols-2">
          {processedViews.map((view) => {
            const raw = view === "front" ? created.raw_front_url : created.raw_back_url;
            const clean = view === "front" ? created.clean_front_url : created.clean_back_url;
            return <div key={view} className="border border-line bg-paper p-4" style={{ borderRadius: 5 }}>
              <div className="mb-3 flex items-center justify-between"><p className="eyebrow text-ink">{view}</p><span className="text-[11px] text-muted">Before → After</span></div>
              <div className="grid grid-cols-2 overflow-hidden border border-line">
                {raw && <img src={assetUrl(raw, created.garment_version)!} alt={`Raw ${view}`} className="aspect-square h-full w-full object-contain" />}
                <div className="image-checker border-l border-line">{clean && <img src={assetUrl(clean, created.garment_version)!} alt={`Clean ${view}`} className="aspect-square h-full w-full object-contain p-3" />}</div>
              </div>
            </div>;
          })}
        </div>
        {!created.clean_back_url && <p className="mx-auto mt-5 max-w-2xl text-center text-xs text-muted">Only the required front view was supplied. The garment is ready to use; its back view remains unavailable.</p>}
        {error && <p className="mx-auto mt-5 max-w-2xl border border-[#dbbbb6] bg-[#fff6f4] p-3 text-xs text-[#8e342e]">{error}</p>}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/" className="secondary-button">Enter wardrobe</Link>
          <button onClick={generateFront} className="primary-button" disabled={saving}>{saving ? <LoaderCircle size={15} className="animate-spin" /> : <Sparkles size={15} />}Generate front view</button>
        </div>
      </main>
    </>;
  }

  return <>
    <SiteHeader compact />
    <main className="mx-auto max-w-[1260px] px-5 py-10 md:px-10 md:py-14">
      <Link href="/" className="focus-ring inline-flex items-center gap-2 text-xs text-muted hover:text-ink"><ArrowLeft size={14} />Back to wardrobe</Link>
      <form onSubmit={submit} className="mt-9 grid gap-10 lg:grid-cols-[340px_minmax(0,1fr)] lg:gap-16">
        <section>
          <p className="eyebrow">Step 2 · Add a piece</p>
          <h1 className="mt-4 font-display text-5xl leading-[.98] tracking-tight">Photograph the garment as it is.</h1>
          <p className="mt-6 text-sm leading-7 text-muted">Lay it flat or hang it against a plain background. Keep every sleeve, hem, and edge visible. We preserve prints, logos, stitching, color, and shape.</p>
          <div className="mt-8 space-y-5">
            <label className="block"><span className="eyebrow mb-2 block text-ink">Garment name</span><input className="field" name="name" required maxLength={120} placeholder="Black essential tee" /></label>
            <label className="block"><span className="eyebrow mb-2 block text-ink">Category</span><select className="field" name="category" defaultValue="T-Shirt">{CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select></label>
            <div className="grid grid-cols-2 gap-3">
              <label><span className="eyebrow mb-2 block text-ink">Brand <em className="font-normal not-italic text-muted">optional</em></span><input className="field" name="brand" maxLength={120} placeholder="Uniqlo" /></label>
              <label><span className="eyebrow mb-2 block text-ink">Color <em className="font-normal not-italic text-muted">optional</em></span><input className="field" name="color" maxLength={80} placeholder="Black" /></label>
            </div>
          </div>
        </section>
        <section>
          <div className="grid grid-cols-2 gap-4 md:gap-6">
            <ImageDropzone label="Front · required" hint="Show the entire front" value={front} onChange={setFront} />
            <ImageDropzone label="Back · optional" hint="Add it whenever available" value={back} onChange={setBack} />
          </div>
          {saving && <div className="mt-5 border border-line bg-paper p-4"><div className="flex items-center gap-3"><LoaderCircle size={17} className="animate-spin" /><div><p className="text-sm font-medium">Cleaning garment {back ? "views" : "view"}</p><p className="mt-1 text-xs text-muted">Transparent PNGs skip background segmentation automatically.</p></div></div></div>}
          {error && <p role="alert" className="mt-5 border border-[#dbbbb6] bg-[#fff6f4] p-3 text-xs leading-5 text-[#8e342e]">{error}</p>}
          <div className="mt-7 flex items-center justify-between">
            <p className="hidden max-w-[280px] text-[11px] leading-5 text-muted sm:block">Front is the only required image. Add the back only when you want a back try-on.</p>
            <button className="primary-button ml-auto" disabled={saving}>{saving ? <>Processing <LoaderCircle size={15} className="animate-spin" /></> : <>Process garment <ArrowRight size={15} /></>}</button>
          </div>
        </section>
      </form>
    </main>
  </>;
}
