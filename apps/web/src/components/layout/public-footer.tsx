export function PublicFooter() {
  return (
    <footer className="border-t border-white/60 bg-background/80">
      <div className="container flex flex-col gap-4 py-10 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between">
        <div>
          <p className="font-display text-base font-semibold text-foreground">CityPulse</p>
          <p>Monorepo scaffold for civic reporting, moderation, and operations.</p>
        </div>
        <p>Prepared for multilingual, AI-assisted, and role-separated product growth.</p>
      </div>
    </footer>
  );
}
