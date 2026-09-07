import { redirect } from "next/navigation";

export default function NewGarmentPage() {
  redirect("/wardrobe?add=1");
}
