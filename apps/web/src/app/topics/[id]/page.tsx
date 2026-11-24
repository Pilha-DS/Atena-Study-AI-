import { redirect } from "next/navigation";

export default async function TopicRedirectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  await params;
  redirect("/courses");
}
