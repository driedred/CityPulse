import { PanelShell } from "@/components/layout/panel-shell";

export default async function AdminLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;

  return (
    <PanelShell
      locale={locale}
      sectionLabel="Admin panel"
      title="Operations, moderation, and civic response"
      description="A separate route group for internal workflows, moderation review, and ticket handling."
      tone="dark"
    >
      {children}
    </PanelShell>
  );
}
