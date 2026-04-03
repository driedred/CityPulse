import { LandingShell } from "@/components/sections/landing-shell";

export default async function PublicLandingPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;

  return <LandingShell locale={locale} />;
}
