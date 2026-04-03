import { PanelShell } from "@/components/layout/panel-shell";
import { appCopy } from "@/content/copy";

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
      sectionLabel={appCopy.panelShell.adminSectionLabel}
      title={appCopy.panelShell.adminTitle}
      description={appCopy.panelShell.adminDescription}
      tone="dark"
    >
      {children}
    </PanelShell>
  );
}
