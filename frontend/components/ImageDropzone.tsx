"use client";
import { ImagePlus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
interface Props { label:string; hint?:string; value:File|null; onChange:(file:File)=>void; existingUrl?:string|null; tall?:boolean; }
const ACCEPT="image/jpeg,image/png,image/webp";
export function ImageDropzone({label,hint,value,onChange,existingUrl,tall=false}:Props) {
  const inputRef=useRef<HTMLInputElement>(null); const [dragging,setDragging]=useState(false); const [preview,setPreview]=useState<string|null>(existingUrl??null);
  useEffect(()=>{ if(!value){setPreview(existingUrl??null);return;} const url=URL.createObjectURL(value);setPreview(url);return()=>URL.revokeObjectURL(url);},[value,existingUrl]);
  function acceptFile(file?:File){if(file&&["image/jpeg","image/png","image/webp"].includes(file.type))onChange(file);}
  return <div><div className="mb-3"><p className="eyebrow text-ink">{label}</p>{hint&&<p className="mt-1 text-xs text-muted">{hint}</p>}</div>
    <button type="button" className={`focus-ring group relative w-full overflow-hidden border bg-paper transition ${dragging?"border-olive":"border-line hover:border-[#aaa69b]"} ${tall?"aspect-[3/4]":"aspect-square"}`} style={{borderRadius:5}} onClick={()=>inputRef.current?.click()} onDragOver={e=>{e.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);acceptFile(e.dataTransfer.files[0])}}>
      {preview?<img src={preview} alt={`${label} preview`} className="h-full w-full object-contain"/>:<span className="flex h-full flex-col items-center justify-center px-5 text-center"><span className="mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-canvas"><ImagePlus size={19} strokeWidth={1.5}/></span><span className="text-sm font-medium">Drop image or browse</span><span className="mt-1 text-xs text-muted">JPG, PNG or WEBP · up to 25 MB</span></span>}
    </button><input ref={inputRef} type="file" accept={ACCEPT} className="sr-only" onChange={e=>acceptFile(e.target.files?.[0])}/></div>;
}
