import { CircleCheck,CircleDashed,CircleX,LoaderCircle } from "lucide-react";
import type { GenerationStatus } from "@/lib/types";
const labels:Record<GenerationStatus,string>={not_generated:"Not generated",processing:"Generating",ready:"Ready",failed:"Needs attention"};
export function StatusPill({status}:{status:GenerationStatus}){const Icon=status==="ready"?CircleCheck:status==="failed"?CircleX:status==="processing"?LoaderCircle:CircleDashed;return <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium ${status==="failed"?"text-[#9b3e35]":status==="ready"?"text-[#4d6344]":"text-muted"}`}><Icon size={12} className={status==="processing"?"animate-spin":""}/>{labels[status]}</span>}
