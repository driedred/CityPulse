"use client";

import type { Route } from "next";
import Link from "next/link";

import { motion } from "framer-motion";
import {
  ArrowRight,
  Building2,
  Globe2,
  ShieldCheck,
  Sparkles,
  Users2,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";

const steps = [
  {
    title: "Capture the issue",
    body: "Citizens submit structured reports with text, media, location, and language context.",
  },
  {
    title: "Moderate and prioritize",
    body: "Backend services and async workers are prepared for AI moderation, scoring, and routing.",
  },
  {
    title: "Resolve with visibility",
    body: "Admins can turn validated reports into tickets and publish updates back to the public surface.",
  },
];

const pillars = [
  {
    icon: Globe2,
    title: "Multilingual-ready",
    body: "Locale-aware routing and content boundaries are built into the app structure from day one.",
  },
  {
    icon: ShieldCheck,
    title: "Moderation-ready",
    body: "Dedicated service and task layers keep future AI review pipelines separate from request transport.",
  },
  {
    icon: Building2,
    title: "Admin aware",
    body: "Citizen and admin panels sit inside the same product while staying logically isolated by route group.",
  },
];

type LandingShellProps = Readonly<{
  locale: string;
}>;

export function LandingShell({ locale }: LandingShellProps) {
  const panels: Array<{
    icon: LucideIcon;
    label: string;
    href: Route;
    body: string;
  }> = [
    {
      icon: Users2,
      label: "Citizen",
      href: `/${locale}/dashboard` as Route,
      body: "Submission, swipe feedback, issue tracking, and community engagement surfaces.",
    },
    {
      icon: Sparkles,
      label: "Admin",
      href: `/${locale}/admin` as Route,
      body: "Moderation, operational tickets, and official public replies for local government teams.",
    },
  ];

  return (
    <main>
      <section className="container relative overflow-hidden py-16 sm:py-20 lg:py-24">
        <div className="absolute inset-x-0 top-8 -z-10 mx-auto h-72 w-72 rounded-full bg-orange-300/30 blur-3xl" />
        <div className="absolute right-0 top-24 -z-10 h-64 w-64 rounded-full bg-sky-300/20 blur-3xl" />

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: "easeOut" }}
          className="mx-auto max-w-5xl"
        >
          <div className="inline-flex rounded-full border border-primary/20 bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.32em] text-primary shadow-soft backdrop-blur">
            Civic reporting for citizens and government bodies
          </div>
          <h1 className="mt-6 max-w-4xl font-display text-5xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-6xl">
            Turn local friction into visible, traceable civic momentum.
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-slate-600 sm:text-lg">
            CityPulse is scaffolded as a full-stack platform for issue reporting, public
            engagement, and government operations. This landing page is intentionally light
            on business logic and heavy on clear product seams.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link href={`/${locale}/dashboard`}>
                Explore citizen shell
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href={`/${locale}/admin`}>Explore admin shell</Link>
            </Button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
          className="mt-12 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]"
        >
          <div className="rounded-[2rem] border border-border/70 bg-white/80 p-6 shadow-soft backdrop-blur sm:p-8">
            <div className="grid gap-4 sm:grid-cols-3">
              {steps.map((step, index) => (
                <article key={step.title} className="rounded-[1.5rem] bg-slate-950 p-5 text-slate-50">
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-orange-300">
                    0{index + 1}
                  </p>
                  <h2 className="mt-4 font-display text-2xl font-semibold">{step.title}</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{step.body}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-primary/15 bg-gradient-to-br from-primary/10 via-white to-sky-100 p-6 shadow-soft sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-primary">
              Product posture
            </p>
            <h2 className="mt-4 font-display text-3xl font-semibold text-slate-950">
              Built for scale without overcommitting early.
            </h2>
            <p className="mt-4 text-sm leading-7 text-slate-600">
              The scaffold separates UX surfaces, API boundaries, domain models, and async
              extension points so moderation, recommendation, and municipality workflows can
              evolve independently.
            </p>
          </div>
        </motion.div>
      </section>

      <section id="how-it-works" className="container py-8 sm:py-14">
        <div className="grid gap-5 lg:grid-cols-3">
          {pillars.map((pillar, index) => {
            const Icon = pillar.icon;

            return (
              <motion.article
                key={pillar.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.45, delay: index * 0.08 }}
                className="rounded-[1.75rem] border border-border/70 bg-white/75 p-6 shadow-soft backdrop-blur"
              >
                <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary text-slate-950">
                  <Icon className="h-6 w-6" />
                </span>
                <h3 className="mt-5 font-display text-2xl font-semibold">{pillar.title}</h3>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{pillar.body}</p>
              </motion.article>
            );
          })}
        </div>
      </section>

      <section id="panels" className="container py-8 sm:py-14">
        <div className="rounded-[2rem] border border-border/70 bg-white/80 p-6 shadow-soft backdrop-blur sm:p-8">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-primary">
                Panels
              </p>
              <h2 className="mt-3 font-display text-3xl font-semibold">
                One product, two clear operational surfaces
              </h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-muted-foreground">
              Route groups keep public, citizen, and admin experiences intentionally separate
              while sharing a single deployable frontend.
            </p>
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-2">
            {panels.map((panel) => {
              const Icon = panel.icon;

              return (
                <Link
                  key={panel.label}
                  href={panel.href}
                  className="group rounded-[1.75rem] border border-border/70 bg-slate-950 p-6 text-slate-50 transition-transform duration-300 hover:-translate-y-1"
                >
                  <Icon className="h-7 w-7 text-orange-300" />
                  <h3 className="mt-4 font-display text-2xl font-semibold">{panel.label} panel</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{panel.body}</p>
                  <span className="mt-6 inline-flex items-center text-sm font-semibold text-orange-300">
                    Open placeholder route
                    <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      <section id="readiness" className="container pb-20 pt-8 sm:pb-24 sm:pt-14">
        <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="rounded-[2rem] border border-border/70 bg-slate-950 p-8 text-slate-50 shadow-soft">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
              Ready states
            </p>
            <h2 className="mt-4 font-display text-3xl font-semibold">
              Foundation before feature density
            </h2>
            <p className="mt-4 text-sm leading-7 text-slate-300">
              The goal of this scaffold is maintainability: clear modules, strict typing,
              route separation, infrastructure defaults, and service seams that can hold up
              once real product logic arrives.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {[
              "FastAPI modules split by API, services, models, middleware, and tasks",
              "Postgres with PostGIS and Redis included in local container orchestration",
              "S3-compatible storage abstraction prepared through backend service contracts",
              "Frontend shell built for mobile-first public, citizen, and admin experiences",
            ].map((item) => (
              <div
                key={item}
                className="rounded-[1.5rem] border border-border/70 bg-white/75 p-5 text-sm leading-6 text-muted-foreground shadow-soft backdrop-blur"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
