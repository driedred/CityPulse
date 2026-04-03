import Link from "next/link";

import { Button } from "@/components/ui/button";

type PanelShellProps = Readonly<{
  children: React.ReactNode;
  locale: string;
  sectionLabel: string;
  title: string;
  description: string;
  tone?: "light" | "dark";
}>;

export function PanelShell({
  children,
  locale,
  sectionLabel,
  title,
  description,
  tone = "light",
}: PanelShellProps) {
  const isDark = tone === "dark";

  return (
    <main
      className={
        isDark
          ? "min-h-screen bg-slate-950 text-slate-50"
          : "min-h-screen bg-gradient-to-b from-background via-white to-slate-100"
      }
    >
      <div className="container py-10">
        <div
          className={
            isDark
              ? "rounded-[2rem] border border-white/10 bg-white/5 p-8 shadow-soft backdrop-blur"
              : "rounded-[2rem] border border-border/70 bg-white/80 p-8 shadow-soft backdrop-blur"
          }
        >
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p
                className={
                  isDark
                    ? "text-xs font-semibold uppercase tracking-[0.35em] text-cyan-200"
                    : "text-xs font-semibold uppercase tracking-[0.35em] text-primary"
                }
              >
                {sectionLabel}
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold">{title}</h1>
              <p
                className={
                  isDark
                    ? "mt-4 text-sm leading-6 text-slate-300"
                    : "mt-4 text-sm leading-6 text-muted-foreground"
                }
              >
                {description}
              </p>
            </div>

            <div className="flex gap-3">
              <Button asChild variant={isDark ? "secondary" : "outline"}>
                <Link href={`/${locale}`}>Public landing</Link>
              </Button>
              <Button asChild variant={isDark ? "outline" : "default"}>
                <Link href={isDark ? `/${locale}/dashboard` : `/${locale}/admin`}>
                  {isDark ? "Citizen view" : "Admin view"}
                </Link>
              </Button>
            </div>
          </div>
        </div>

        <div className="mt-8">{children}</div>
      </div>
    </main>
  );
}
