const adminCards = [
  {
    title: "Moderation queue",
    description: "Reserved for AI-assisted review states and escalation workflows.",
  },
  {
    title: "Operational tickets",
    description: "Reserved for municipality-facing assignment and execution tracking.",
  },
  {
    title: "Citizen responses",
    description: "Reserved for public replies, status updates, and audit-friendly notes.",
  },
];

export default function AdminDashboardPage() {
  return (
    <section className="grid gap-6 xl:grid-cols-[1fr_1fr_1fr]">
      {adminCards.map((card) => (
        <article
          key={card.title}
          className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
            Internal
          </p>
          <h2 className="mt-4 font-display text-2xl font-semibold text-white">
            {card.title}
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-300">{card.description}</p>
        </article>
      ))}
    </section>
  );
}
