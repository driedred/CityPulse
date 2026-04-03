const citizenCards = [
  {
    title: "Report submission",
    description: "Structured issue creation flow with media upload and location capture.",
  },
  {
    title: "Swipe queue",
    description: "Card-based discovery feed prepared for ranking and recommendation signals.",
  },
  {
    title: "Issue tracking",
    description: "Space for lifecycle updates, admin replies, and ticket visibility.",
  },
];

export default function CitizenDashboardPage() {
  return (
    <section className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
      <div className="rounded-[1.75rem] border border-border/70 bg-white/80 p-6 shadow-soft backdrop-blur">
        <span className="text-xs font-semibold uppercase tracking-[0.3em] text-primary">
          Coming next
        </span>
        <h2 className="mt-3 font-display text-3xl font-semibold">
          Citizen workflow foundations
        </h2>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">
          This route group is reserved for the authenticated citizen experience. The
          scaffold keeps reporting, discovery, and account-level features isolated from
          public marketing pages and admin operations.
        </p>
      </div>

      <div className="rounded-[1.75rem] border border-border/70 bg-slate-900 p-6 text-slate-50 shadow-soft">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-amber-300">
          Platform mode
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Mobile-first card flows, multilingual routing, and future AI ranking hooks are
          already reflected in the directory layout.
        </p>
      </div>

      {citizenCards.map((card) => (
        <article
          key={card.title}
          className="rounded-[1.5rem] border border-border/70 bg-white/70 p-5 shadow-soft backdrop-blur"
        >
          <h3 className="font-display text-xl font-semibold">{card.title}</h3>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">{card.description}</p>
        </article>
      ))}
    </section>
  );
}
