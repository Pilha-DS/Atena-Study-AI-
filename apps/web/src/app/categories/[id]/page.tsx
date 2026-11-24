import { redirect } from "next/navigation";

export default async function CategoryRedirectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  await params;
  redirect("/courses");
}
