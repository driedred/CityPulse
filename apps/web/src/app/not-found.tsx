import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="max-w-md rounded-[2rem] border border-border/80 bg-white/80 p-8 text-center shadow-soft backdrop-blur">
        <p className="font-display text-sm uppercase tracking-[0.3em] text-muted-foreground">
          CityPulse
        </p>
        <h1 className="mt-4 font-display text-3xl font-semibold">Route not found</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          The requested locale or page is not part of this scaffold yet.
        </p>
        <Link
          href="/en"
          className="mt-6 inline-flex rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground"
        >
          Return to landing
        </Link>
      </div>
    </main>
  );
}
