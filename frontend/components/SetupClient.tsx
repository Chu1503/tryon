"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Grid2X2, Home, LoaderCircle, Save } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, assetUrl } from "@/lib/api";
import { ImageDropzone } from "./ImageDropzone";

export function SetupClient() {
  const queryClient = useQueryClient();
  const user = useQuery({ queryKey: ["user"], queryFn: api.getUser });
  const [name, setName] = useState("CHU");
  const [front, setFront] = useState<File | null>(null);
  const [back, setBack] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user.data?.display_name) setName(user.data.display_name);
  }, [user.data?.display_name]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    if (!user.data?.body_front_url && !front) {
      setError("Front body image is required.");
      return;
    }
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      let updated = await api.updateProfile(name.trim());
      if (front || back) {
        const body = new FormData();
        if (front) body.set("front", front);
        if (back) body.set("back", back);
        updated = await api.uploadBody(body);
      }
      queryClient.setQueryData(["user"], updated);
      setFront(null);
      setBack(null);
      setSaved(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Profile could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  if (user.isLoading || !user.data) return <div className="sketch-loading"><span /></div>;

  return <main className="profile-page">
    <header className="collection-topbar">
      <Link href="/" className="collection-icon" aria-label="Home"><Home /></Link>
      <span className="collection-name">{name.toUpperCase()}</span>
      <Link href="/wardrobe" className="collection-icon" aria-label="Wardrobe"><Grid2X2 /></Link>
    </header>

    <form className="profile-layout" onSubmit={submit}>
      <section className="profile-controls">
        <label className="profile-name-field"><span>NAME</span><input value={name} onChange={(event) => setName(event.target.value)} maxLength={80} /></label>
        <div className="profile-photo-grid">
          <ImageDropzone label="FRONT · REQUIRED" value={front} onChange={setFront} existingUrl={assetUrl(user.data.body_front_url, user.data.body_reference_version)} tall />
          <ImageDropzone label="BACK · OPTIONAL" value={back} onChange={setBack} existingUrl={assetUrl(user.data.body_back_url, user.data.body_reference_version)} tall />
        </div>
        {error && <p className="collection-error" role="alert">{error}</p>}
        <button className="profile-save" disabled={saving}>{saving ? <LoaderCircle className="animate-spin" /> : <Save />}{saving ? "PREPARING CUTOUT" : saved ? "SAVED" : "SAVE"}</button>
      </section>
    </form>
  </main>;
}
