"use client";

import type { Route } from "next";
import Link from "next/link";
import { useEffect, useState, useTransition } from "react";

import { ShieldAlert, Sparkles } from "lucide-react";

import { AuthRequiredCard } from "@/components/auth/auth-required-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineMessage } from "@/components/ui/inline-message";
import { PageLoading } from "@/components/ui/page-loading";
import { appCopy } from "@/content/copy";
import { formatIssueDate } from "@/features/issues/lib/presenters";
import { useAdminIntegrityUsers } from "@/features/admin-integrity/hooks/use-admin-integrity";
import {
  useAdminModerationIssueDetail,
  useAdminModerationIssues,
} from "@/features/admin-moderation/hooks/use-admin-moderation";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

type AdminModerationScreenProps = Readonly<{
  locale: string;
}>;

function formatLayerLabel(layer: "deterministic" | "llm") {
  return layer === "deterministic"
    ? appCopy.adminModeration.stageDeterministic
    : appCopy.adminModeration.stageLlm;
}

function formatDecisionLabel(status: string) {
  if (status === "approved") {
    return appCopy.common.approved;
  }
  if (status === "rejected") {
    return appCopy.common.rejected;
  }
  return appCopy.common.manualReview;
}

function formatRiskLabel(level: "low" | "medium" | "high") {
  if (level === "high") {
    return appCopy.common.high;
  }
  if (level === "medium") {
    return appCopy.common.medium;
  }
  return appCopy.common.low;
}

export function AdminModerationScreen({ locale }: AdminModerationScreenProps) {
  const { token, user } = useAuth();
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const isAdmin = user?.role === "admin";
  const issues = useAdminModerationIssues(token, Boolean(isAdmin));
  const detail = useAdminModerationIssueDetail(token, selectedIssueId, Boolean(isAdmin));
  const watchlist = useAdminIntegrityUsers(token, Boolean(isAdmin));

  useEffect(() => {
    if (!selectedIssueId && issues.data.length) {
      setSelectedIssueId(issues.data[0].id);
    }
  }, [issues.data, selectedIssueId]);

  if (!user) {
    return <AuthRequiredCard locale={locale} />;
  }

  if (!isAdmin) {
    return <InlineMessage variant="error">{appCopy.adminModeration.adminOnly}</InlineMessage>;
  }

  function rerunModeration() {
    if (!token || !selectedIssueId) {
      return;
    }

    startTransition(async () => {
      try {
        const audit = await apiClient.rerunAdminModerationIssue(token, selectedIssueId);
        detail.setData(audit);
        issues.reload();
        setNotice(appCopy.discover.savedAction);
      } catch (error) {
        setNotice(error instanceof Error ? error.message : appCopy.issueViews.errorTitle);
      }
    });
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
      <div className="space-y-5">
        <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
            {appCopy.adminModeration.eyebrow}
          </p>
          <h1 className="mt-4 font-display text-3xl font-semibold text-white">
            {appCopy.adminModeration.title}
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            {appCopy.adminModeration.description}
          </p>
        </div>

        {notice ? <InlineMessage variant="info">{notice}</InlineMessage> : null}

        {issues.error ? (
          <InlineMessage variant="error">{issues.error}</InlineMessage>
        ) : null}

        {issues.isLoading ? (
          <PageLoading title={appCopy.common.loading} />
        ) : issues.data.length ? (
          <div className="grid gap-4">
            {issues.data.map((issue) => (
              <button
                key={issue.id}
                type="button"
                onClick={() => setSelectedIssueId(issue.id)}
                className={
                  selectedIssueId === issue.id
                    ? "rounded-[1.5rem] border border-cyan-300/40 bg-cyan-300/10 p-5 text-left"
                    : "rounded-[1.5rem] border border-white/10 bg-white/5 p-5 text-left"
                }
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="accent">{issue.category.display_name}</Badge>
                  {issue.latest_moderation ? (
                    <Badge variant="primary">
                      {formatLayerLabel(issue.latest_moderation.layer)}
                    </Badge>
                  ) : null}
                  <Badge variant="subtle">
                    {formatDecisionLabel(issue.latest_moderation?.status ?? "needs_review")}
                  </Badge>
                </div>
                <h2 className="mt-4 font-display text-2xl font-semibold text-white">
                  {issue.title}
                </h2>
                <p className="mt-3 text-sm leading-6 text-slate-300">
                  {issue.short_description}
                </p>
                <div className="mt-4 flex flex-wrap gap-3 text-xs uppercase tracking-[0.2em] text-slate-400">
                  <span>{formatIssueDate(issue.created_at)}</span>
                  <span>
                    {issue.attachment_count} {appCopy.adminModeration.attachmentLabel}
                  </span>
                  {issue.author ? (
                    <span>
                      {appCopy.adminModeration.authorLabel}: {issue.author.user.full_name}
                    </span>
                  ) : null}
                </div>
                {issue.author ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge variant="subtle">
                      {appCopy.adminModeration.trustScoreLabel}:{" "}
                      {issue.author.trust_score.toFixed(1)}
                    </Badge>
                    <Badge
                      variant={
                        issue.author.abuse_risk_level === "high"
                          ? "accent"
                          : issue.author.abuse_risk_level === "medium"
                            ? "primary"
                            : "subtle"
                      }
                    >
                      {appCopy.adminModeration.abuseRiskLabel}:{" "}
                      {formatRiskLabel(issue.author.abuse_risk_level)}
                    </Badge>
                  </div>
                ) : null}
              </button>
            ))}
          </div>
        ) : (
          <EmptyState
            title={appCopy.adminModeration.emptyTitle}
            body={appCopy.adminModeration.emptyBody}
          />
        )}
      </div>

      <div className="space-y-5">
        <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
                {appCopy.adminModeration.detailTitle}
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                {appCopy.adminModeration.queueBody}
              </p>
            </div>
            <Button type="button" variant="secondary" onClick={rerunModeration} disabled={isPending}>
              {isPending ? appCopy.common.loading : appCopy.adminModeration.rerunAction}
            </Button>
          </div>
        </div>

        {detail.error ? (
          <InlineMessage variant="error">{detail.error}</InlineMessage>
        ) : null}

        {detail.isLoading ? (
          <PageLoading title={appCopy.common.loading} />
        ) : detail.data ? (
          <div className="space-y-4">
            {detail.data.author ? (
              <article className="rounded-[1.5rem] border border-cyan-300/15 bg-cyan-300/5 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-100">
                      {appCopy.adminModeration.authorLabel}
                    </p>
                    <h2 className="mt-2 font-display text-2xl font-semibold text-white">
                      {detail.data.author.user.full_name}
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {detail.data.author.summary ?? appCopy.common.none}
                    </p>
                  </div>
                  <Button asChild type="button" variant="outline">
                    <Link href={`/${locale}/admin/users/${detail.data.author.user.id}` as Route}>
                      {appCopy.adminModeration.openUserAction}
                    </Link>
                  </Button>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge variant="subtle">
                    {appCopy.adminModeration.trustScoreLabel}:{" "}
                    {detail.data.author.trust_score.toFixed(1)}
                  </Badge>
                  <Badge variant="subtle">
                    {appCopy.adminModeration.weightLabel}:{" "}
                    {detail.data.author.trust_weight_multiplier.toFixed(3)}
                  </Badge>
                  <Badge
                    variant={
                      detail.data.author.abuse_risk_level === "high"
                        ? "accent"
                        : detail.data.author.abuse_risk_level === "medium"
                          ? "primary"
                          : "subtle"
                    }
                  >
                    {appCopy.adminModeration.abuseRiskLabel}:{" "}
                    {formatRiskLabel(detail.data.author.abuse_risk_level)}
                  </Badge>
                </div>
              </article>
            ) : null}

            {detail.data.results.map((result) => (
              <article
                key={result.id}
                className="rounded-[1.5rem] border border-white/10 bg-slate-900/70 p-5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="primary">{formatLayerLabel(result.layer)}</Badge>
                  <Badge variant="subtle">{formatDecisionLabel(result.status)}</Badge>
                  {result.escalation_required ? (
                    <Badge variant="accent">{appCopy.common.manualReview}</Badge>
                  ) : null}
                </div>

                <div className="mt-4 grid gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                      {appCopy.adminModeration.latestDecisionLabel}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-200">{result.summary}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                      {appCopy.adminModeration.userExplanationLabel}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-200">
                      {result.user_safe_explanation ?? appCopy.common.none}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                      {appCopy.adminModeration.internalNotesLabel}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {result.internal_notes ?? appCopy.common.none}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                      {appCopy.adminModeration.machineReasonsLabel}
                    </p>
                    {result.machine_reasons.length ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {result.machine_reasons.map((reason) => (
                          <Badge key={`${result.id}-${reason.code}`} variant="subtle">
                            {reason.label}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-2 text-sm leading-6 text-slate-300">
                        {appCopy.common.none}
                      </p>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-[1.5rem] border border-dashed border-white/15 bg-white/5 p-8 text-center text-slate-300">
            <ShieldAlert className="mx-auto h-10 w-10 text-cyan-200" />
            <p className="mt-4">{appCopy.adminModeration.emptyBody}</p>
          </div>
        )}

        <div className="rounded-[1.5rem] border border-cyan-300/10 bg-cyan-300/5 p-5">
          <div className="flex items-center gap-2 text-cyan-100">
            <Sparkles className="h-4 w-4" />
            <p className="text-sm font-semibold">{appCopy.adminModeration.queueTitle}</p>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            {appCopy.adminModeration.queueBody}
          </p>
        </div>

        <div className="rounded-[1.5rem] border border-white/10 bg-slate-900/70 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            {appCopy.adminModeration.watchlistTitle}
          </p>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            {appCopy.adminModeration.watchlistBody}
          </p>
          {watchlist.error ? (
            <InlineMessage variant="error">{watchlist.error}</InlineMessage>
          ) : null}
          {watchlist.data.length ? (
            <div className="mt-4 grid gap-3">
              {watchlist.data.slice(0, 6).map((entry) => (
                <Link
                  key={entry.user.id}
                  href={`/${locale}/admin/users/${entry.user.id}` as Route}
                  className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4 transition-colors hover:bg-white/10"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="subtle">{entry.user.role}</Badge>
                    <Badge
                      variant={
                        entry.abuse_risk_level === "high"
                          ? "accent"
                          : entry.abuse_risk_level === "medium"
                            ? "primary"
                            : "subtle"
                      }
                    >
                      {appCopy.adminModeration.abuseRiskLabel}:{" "}
                      {formatRiskLabel(entry.abuse_risk_level)}
                    </Badge>
                  </div>
                  <p className="mt-3 font-semibold text-white">{entry.user.full_name}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    {entry.summary ?? appCopy.common.none}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-3 text-xs uppercase tracking-[0.2em] text-slate-400">
                    <span>
                      {appCopy.adminModeration.trustScoreLabel}: {entry.trust_score.toFixed(1)}
                    </span>
                    <span>
                      {appCopy.adminModeration.weightLabel}:{" "}
                      {entry.trust_weight_multiplier.toFixed(3)}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
