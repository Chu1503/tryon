import Link from "next/link";
import { Plus, ScanFace } from "lucide-react";
export function SiteHeader({ compact=false }:{compact?:boolean}) {
  return <header className="border-b border-line bg-paper/95"><div className={`mx-auto flex max-w-[1500px] items-center justify-between px-5 ${compact?"h-[72px]":"h-[82px]"} md:px-10`}>
    <Link href="/" className="focus-ring group flex items-center gap-3" aria-label="Digital Wardrobe home">
      <span className="flex h-9 w-9 items-center justify-center border border-ink bg-ink text-white" style={{borderRadius:3}}><ScanFace size={17} strokeWidth={1.5}/></span>
      <span><span className="block text-[10px] font-semibold uppercase tracking-[.27em] text-muted">Private collection</span><span className="font-display text-[23px] leading-none tracking-tight">Digital Wardrobe</span></span>
    </Link>
    <nav className="flex items-center gap-2" aria-label="Primary navigation"><Link href="/setup" className="focus-ring hidden px-3 py-2 text-sm text-muted hover:text-ink sm:block">Body photos</Link><Link href="/garments/new" className="primary-button h-10 px-4"><Plus size={16}/><span className="hidden sm:inline">Add garment</span><span className="sm:hidden">Add</span></Link></nav>
  </div></header>;
}
