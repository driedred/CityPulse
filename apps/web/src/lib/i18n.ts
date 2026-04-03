const envLocales = process.env.NEXT_PUBLIC_SUPPORTED_LOCALES;

export const supportedLocales = (envLocales?.split(",").map((locale) => locale.trim()).filter(Boolean) as
  | string[]
  | undefined) ?? ["en", "es"];

export type AppLocale = (typeof supportedLocales)[number];

export const defaultLocale = process.env.NEXT_PUBLIC_DEFAULT_LOCALE ?? supportedLocales[0] ?? "en";

export function isSupportedLocale(locale: string): locale is AppLocale {
  return supportedLocales.includes(locale);
}
