import Link from "next/link";

import { Button } from "@/components/ui/button";
import { siteConfig } from "@/lib/site";

type PublicHeaderProps = Readonly<{
  locale: string;
}>;

export function PublicHeader({ locale }: PublicHeaderProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-white/60 bg-background/80 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between gap-4">
        <Link href={`/${locale}`} className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground">
            CP
          </span>
          <div>
            <p className="font-display text-lg font-semibold">{siteConfig.name}</p>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
              Civic signal platform
            </p>
          </div>
        </Link>

        <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
          <Link href="#how-it-works">How it works</Link>
          <Link href="#panels">Panels</Link>
          <Link href="#readiness">Readiness</Link>
        </nav>

        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" className="hidden sm:inline-flex">
            <Link href={`/${locale}/dashboard`}>Citizen panel</Link>
          </Button>
          <Button asChild>
            <Link href={`/${locale}/admin`}>Admin panel</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
