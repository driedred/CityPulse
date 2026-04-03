import { PanelShell } from "@/components/layout/panel-shell";

export default async function UserLayout({
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
      sectionLabel="Citizen panel"
      title="Local issues, prioritized for action"
      description="A citizen-facing shell for discovery, submission, tracking, and engagement."
    >
      {children}
    </PanelShell>
  );
}
