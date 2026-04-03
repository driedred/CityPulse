import { AdminModerationScreen } from "@/features/admin-moderation/components/admin-moderation-screen";

export default async function AdminDashboardPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;

  return <AdminModerationScreen locale={locale} />;
}
