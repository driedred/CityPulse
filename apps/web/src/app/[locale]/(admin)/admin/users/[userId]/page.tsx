import { AdminUserIntegrityScreen } from "@/features/admin-integrity/components/admin-user-integrity-screen";

export default async function AdminUserIntegrityPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string; userId: string }>;
}>) {
  const { locale, userId } = await params;

  return <AdminUserIntegrityScreen locale={locale} userId={userId} />;
}
