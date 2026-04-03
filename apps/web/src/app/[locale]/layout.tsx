import { notFound } from "next/navigation";

import { isSupportedLocale, supportedLocales, type AppLocale } from "@/lib/i18n";

export function generateStaticParams() {
  return supportedLocales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  return (
    <div data-locale={locale as AppLocale} className="min-h-screen">
      {children}
    </div>
  );
}
