"use client";

import Link from "next/link";
import { useState, useTransition } from "react";

import { AlertTriangle, ShieldCheck, ShieldQuestion } from "lucide-react";

import { AuthRequiredCard } from "@/components/auth/auth-required-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineMessage } from "@/components/ui/inline-message";
import { PageLoading } from "@/components/ui/page-loading";
import { appCopy } from "@/content/copy";
import { formatIssueDate } from "@/features/issues/lib/presenters";
import { useAdminUserIntegrityDetail } from "@/features/admin-integrity/hooks/use-admin-integrity";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";
import type {
  AbuseRiskLevel,
  IntegrityEventSeverity,
  IntegrityFactor,
  UserIntegrityDetail,
} from "@/lib/api/types";

type AdminUserIntegrityScreenProps = Readonly<{
  locale: string;
  userId: string;
}>;

function getRiskLabel(level: AbuseRiskLevel) {
  if (level === "high") {
    return appCopy.common.high;
  }
  if (level === "medium") {
    return appCopy.common.medium;
  }
  return appCopy.common.low;
}

function getSeverityLabel(level: IntegrityEventSeverity) {
  if (level === "high") {
    return appCopy.common.high;
  }
  if (level === "medium") {
    return appCopy.common.medium;
  }
  return appCopy.common.low;
}

function getRiskBadgeVariant(level: AbuseRiskLevel): "primary" | "accent" | "subtle" {
  if (level === "high") {
    return "accent";
  }
  if (level === "medium") {
    return "primary";
  }
  return "subtle";
}

function getSeverityBadgeVariant(
  level: IntegrityEventSeverity,
): "primary" | "accent" | "subtle" {
  if (level === "high") {
    return "accent";
  }
  if (level === "medium") {
    return "primary";
  }
  return "subtle";
}

function formatMetricValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === "string") {
    return value;
  }
  return appCopy.common.none;
}

function renderFactorList(factors: IntegrityFactor[], emptyLabel: string) {
  if (!factors.length) {
    return <p className="text-sm leading-6 text-slate-300">{emptyLabel}</p>;
  }

  return (
    <div className="grid gap-3">
      {factors.map((factor) => (
        <article
          key={factor.name}
          className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={factor.effect === "risk" ? "accent" : "primary"}>
              {factor.label}
            </Badge>
            {typeof factor.signal === "number" ? (
              <Badge variant="subtle">{factor.signal.toFixed(2)}</Badge>
            ) : null}
            {typeof factor.points === "number" ? (
              <Badge variant="subtle">{factor.points.toFixed(2)}</Badge>
            ) : null}
          </div>
          {Object.keys(factor.details).length ? (
            <div className="mt-3 flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-slate-400">
              {Object.entries(factor.details).map(([key, value]) => (
                <span key={key}>
                  {key}: {formatMetricValue(value)}
                </span>
              ))}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function renderSummaryCards(detail: UserIntegrityDetail) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
          {appCopy.adminModeration.trustScoreLabel}
        </p>
        <p className="mt-3 font-display text-3xl font-semibold text-white">
          {detail.trust_score.toFixed(1)}
        </p>
      </article>
      <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
          {appCopy.adminModeration.weightLabel}
        </p>
        <p className="mt-3 font-display text-3xl font-semibold text-white">
          {detail.trust_weight_multiplier.toFixed(3)}
        </p>
      </article>
      <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
          {appCopy.adminModeration.abuseRiskLabel}
        </p>
        <div className="mt-3 flex items-center gap-3">
          <Badge variant={getRiskBadgeVariant(detail.abuse_risk_level)}>
            {getRiskLabel(detail.abuse_risk_level)}
          </Badge>
          <span className="font-display text-3xl font-semibold text-white">
            {detail.abuse_risk_score.toFixed(1)}
          </span>
        </div>
      </article>
      <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
          {appCopy.adminIntegrity.sanctionsLabel}
        </p>
        <p className="mt-3 font-display text-3xl font-semibold text-white">
          {detail.sanction_count}
        </p>
      </article>
    </div>
  );
}

export function AdminUserIntegrityScreen({
  locale,
  userId,
}: AdminUserIntegrityScreenProps) {
  const { token, user } = useAuth();
  const [notice, setNotice] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const isAdmin = user?.role === "admin";
  const detail = useAdminUserIntegrityDetail(token, userId, Boolean(isAdmin));

  if (!user) {
    return <AuthRequiredCard locale={locale} />;
  }

  if (!isAdmin) {
    return <InlineMessage variant="error">{appCopy.adminIntegrity.adminOnly}</InlineMessage>;
  }

  function handleRecalculate() {
    if (!token) {
      return;
    }

    startTransition(async () => {
      try {
        const nextDetail = await apiClient.recalculateAdminUserIntegrity(token, userId);
        detail.setData(nextDetail);
        setNotice(appCopy.discover.savedAction);
      } catch (error) {
        setNotice(error instanceof Error ? error.message : appCopy.issueViews.errorTitle);
      }
    });
  }

  if (detail.isLoading) {
    return <PageLoading title={appCopy.common.loading} />;
  }

  if (detail.error) {
    return <InlineMessage variant="error">{detail.error}</InlineMessage>;
  }

  if (!detail.data) {
    return (
      <EmptyState
        title={appCopy.adminIntegrity.title}
        body={appCopy.adminIntegrity.noUser}
      />
    );
  }

  const current = detail.data;

  return (
    <section className="space-y-6">
      <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
              {appCopy.adminIntegrity.title}
            </p>
            <h1 className="mt-4 font-display text-3xl font-semibold text-white">
              {current.user.full_name}
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {appCopy.adminIntegrity.description}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild type="button" variant="secondary">
              <Link href={`/${locale}/admin`}>{appCopy.adminIntegrity.backToModeration}</Link>
            </Button>
            <Button type="button" variant="outline" onClick={handleRecalculate} disabled={isPending}>
              {isPending ? appCopy.common.loading : appCopy.adminIntegrity.recalculateAction}
            </Button>
          </div>
        </div>
      </div>

      {notice ? <InlineMessage variant="info">{notice}</InlineMessage> : null}

      {renderSummaryCards(current)}

      <div className="grid gap-6 xl:grid-cols-[0.76fr_1.24fr]">
        <div className="space-y-6">
          <article className="rounded-[1.5rem] border border-white/10 bg-slate-900/70 p-5">
            <div className="flex items-center gap-2 text-cyan-100">
              <ShieldCheck className="h-4 w-4" />
              <p className="text-sm font-semibold">{appCopy.adminIntegrity.userMetaTitle}</p>
            </div>
            <div className="mt-4 grid gap-4 text-sm text-slate-200">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {appCopy.adminIntegrity.emailLabel}
                </p>
                <p className="mt-2">{current.user.email}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {appCopy.adminIntegrity.roleLabel}
                </p>
                <p className="mt-2">{current.user.role}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {appCopy.adminIntegrity.localeLabel}
                </p>
                <p className="mt-2">{current.user.preferred_locale}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {appCopy.adminIntegrity.joinedLabel}
                </p>
                <p className="mt-2">{formatIssueDate(current.user.created_at)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {appCopy.adminIntegrity.lastLoginLabel}
                </p>
                <p className="mt-2">
                  {current.user.last_login_at
                    ? formatIssueDate(current.user.last_login_at)
                    : appCopy.common.none}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {appCopy.adminIntegrity.updatedLabel}
                </p>
                <p className="mt-2">{formatIssueDate(current.updated_at)}</p>
              </div>
            </div>
          </article>

          <article className="rounded-[1.5rem] border border-white/10 bg-slate-900/70 p-5">
            <div className="flex items-center gap-2 text-cyan-100">
              <ShieldQuestion className="h-4 w-4" />
              <p className="text-sm font-semibold">{appCopy.adminIntegrity.summaryLabel}</p>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-200">
              {current.summary ?? appCopy.common.none}
            </p>
            {current.recommended_actions.length ? (
              <div className="mt-4 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {appCopy.adminIntegrity.recommendedActionsTitle}
                </p>
                <div className="grid gap-2">
                  {current.recommended_actions.map((action) => (
                    <div
                      key={action}
                      className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200"
                    >
                      {action}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </article>

          <article className="rounded-[1.5rem] border border-white/10 bg-slate-900/70 p-5">
            <div className="flex items-center gap-2 text-cyan-100">
              <AlertTriangle className="h-4 w-4" />
              <p className="text-sm font-semibold">{appCopy.adminIntegrity.recentEventsTitle}</p>
            </div>
            {current.recent_events.length ? (
              <div className="mt-4 grid gap-3">
                {current.recent_events.map((event) => (
                  <article
                    key={event.id}
                    className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={getSeverityBadgeVariant(event.severity)}>
                        {getSeverityLabel(event.severity)}
                      </Badge>
                      <Badge variant="subtle">{event.event_type}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-200">{event.summary}</p>
                    <div className="mt-3 flex flex-wrap gap-3 text-xs uppercase tracking-[0.2em] text-slate-400">
                      <span>{formatIssueDate(event.created_at)}</span>
                      {event.entity_type ? <span>{event.entity_type}</span> : null}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm leading-6 text-slate-300">
                {appCopy.adminIntegrity.emptyEvents}
              </p>
            )}
          </article>
        </div>

        <div className="space-y-6">
          <article className="rounded-[1.5rem] border border-white/10 bg-slate-900/70 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
              {appCopy.adminIntegrity.trustFactorsTitle}
            </p>
            <div className="mt-4">
              {renderFactorList(current.trust_factors, appCopy.adminIntegrity.emptyFactors)}
            </div>
          </article>

          <article className="rounded-[1.5rem] border border-white/10 bg-slate-900/70 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
              {appCopy.adminIntegrity.abuseFactorsTitle}
            </p>
            <div className="mt-4">
              {renderFactorList(current.abuse_factors, appCopy.adminIntegrity.emptyFactors)}
            </div>
          </article>

          <article className="rounded-[1.5rem] border border-white/10 bg-slate-900/70 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
              {appCopy.adminIntegrity.metricsTitle}
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {Object.entries(current.metrics).map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-[1.25rem] border border-white/10 bg-white/5 px-4 py-3"
                >
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{key}</p>
                  <p className="mt-2 text-sm text-slate-100">{formatMetricValue(value)}</p>
                </div>
              ))}
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
