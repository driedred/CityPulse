"use client";

import type { Route } from "next";
import Link from "next/link";

import { ArrowRight, Radar } from "lucide-react";

import { AuthRequiredCard } from "@/components/auth/auth-required-card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineMessage } from "@/components/ui/inline-message";
import { PageLoading } from "@/components/ui/page-loading";
import {
  DistributionList,
  SimpleBarChart,
  TrendChart,
} from "@/features/admin-console/components/admin-charts";
import {
  AdminKeyValueGrid,
  AdminMetricCard,
  AdminSectionHeader,
  AdminStatusBadge,
  AdminSurface,
} from "@/features/admin-console/components/admin-primitives";
import { useAdminDashboard, useAdminDuplicateConcentration, useAdminSupportTrends, useAdminTopAreas } from "@/features/admin-console/hooks/use-admin-console";
import {
  formatCompactNumber,
  formatIssueDate,
  formatIssueStatus,
  formatLifecycleLabel,
  formatStatusTone,
} from "@/features/admin-console/lib/presenters";
import { IssueHeatmapMap } from "@/features/issues/components/issue-heatmap-map";
import { useAuth } from "@/lib/auth/auth-provider";
import { useAdminCopy } from "@/lib/i18n-provider";

type AdminDashboardScreenProps = Readonly<{
  locale: string;
}>;

export function AdminDashboardScreen({ locale }: AdminDashboardScreenProps) {
  const adminConsoleCopy = useAdminCopy();
  const { token, user } = useAuth();
  const isAdmin = user?.role === "admin";
  const dashboard = useAdminDashboard(token, Boolean(isAdmin));
  const supportTrends = useAdminSupportTrends(token, Boolean(isAdmin), "week", 10);
  const topAreas = useAdminTopAreas(token, Boolean(isAdmin), 8);
  const duplicateConcentration = useAdminDuplicateConcentration(
    token,
    Boolean(isAdmin),
    8,
  );

  if (!user) {
    return <AuthRequiredCard locale={locale} />;
  }

  if (!isAdmin) {
    return <InlineMessage variant="error">{adminConsoleCopy.common.adminOnly}</InlineMessage>;
  }

  const error =
    dashboard.error ||
    supportTrends.error ||
    topAreas.error ||
    duplicateConcentration.error;

  if (dashboard.isLoading && !dashboard.data) {
    return <PageLoading title={adminConsoleCopy.common.loading} />;
  }

  if (error) {
    return <InlineMessage variant="error">{error}</InlineMessage>;
  }

  if (!dashboard.data) {
    return (
      <EmptyState
        title={adminConsoleCopy.common.noData}
        body={adminConsoleCopy.dashboard.description}
      />
    );
  }

  const current = dashboard.data;
  const supportActionsTotal =
    current.reaction_overview.support_count +
    current.reaction_overview.more_like_this_count;
  const issueTrendPoints = current.activity_trends.map((point) => ({
    label: point.label,
    value: point.issue_submissions,
  }));
  const ticketTrendPoints = current.activity_trends.map((point) => ({
    label: point.label,
    value: point.tickets_created,
  }));
  const supportTrendPoints = supportTrends.data.map((point) => ({
    label: point.label,
    value: point.support + point.more_like_this,
  }));

  return (
    <section className="space-y-6">
      <AdminSurface>
        <AdminSectionHeader
          eyebrow={adminConsoleCopy.dashboard.eyebrow}
          title={adminConsoleCopy.dashboard.title}
          body={adminConsoleCopy.dashboard.description}
          action={
            <Button asChild variant="secondary">
              <Link href={`/${locale}/admin/heatmap` as Route}>
                <Radar className="mr-2 h-4 w-4" />
                {adminConsoleCopy.shell.sections.heatmap}
              </Link>
            </Button>
          }
        />
      </AdminSurface>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
        <AdminMetricCard
          label={adminConsoleCopy.dashboard.cards.totalIssues}
          value={formatCompactNumber(current.issue_volume.total_issues)}
        />
        <AdminMetricCard
          label={adminConsoleCopy.dashboard.cards.newThisWeek}
          value={formatCompactNumber(current.issue_volume.new_last_7_days)}
          tone="accent"
        />
        <AdminMetricCard
          label={adminConsoleCopy.dashboard.cards.averageTrust}
          value={current.trust_overview.average_trust_score.toFixed(1)}
        />
        <AdminMetricCard
          label={adminConsoleCopy.dashboard.cards.ticketQueue}
          value={formatCompactNumber(current.ticket_queue.open_count)}
        />
        <AdminMetricCard
          label={adminConsoleCopy.dashboard.cards.published}
          value={formatCompactNumber(current.issue_volume.published_count)}
          tone="primary"
        />
        <AdminMetricCard
          label={adminConsoleCopy.dashboard.cards.pending}
          value={formatCompactNumber(current.issue_volume.pending_count)}
        />
        <AdminMetricCard
          label={adminConsoleCopy.dashboard.cards.highAbuse}
          value={formatCompactNumber(current.trust_overview.high_abuse_risk_users)}
          tone="accent"
        />
        <AdminMetricCard
          label={adminConsoleCopy.dashboard.cards.supportActions}
          value={formatCompactNumber(supportActionsTotal)}
          hint={formatCompactNumber(current.reaction_overview.support_count)}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <AdminSurface>
          <AdminSectionHeader
            title={adminConsoleCopy.dashboard.charts.activityTitle}
            body={adminConsoleCopy.dashboard.charts.activityBody}
          />
          <div className="mt-6 grid gap-6">
            <div>
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {adminConsoleCopy.dashboard.cards.totalIssues}
              </p>
              <TrendChart
                points={issueTrendPoints}
                emptyLabel={adminConsoleCopy.common.noData}
              />
            </div>
            <div>
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {adminConsoleCopy.dashboard.cards.ticketQueue}
              </p>
              <TrendChart
                points={ticketTrendPoints}
                emptyLabel={adminConsoleCopy.common.noData}
                colorClassName="from-emerald-300 to-cyan-300"
              />
            </div>
          </div>
        </AdminSurface>

        <AdminSurface>
          <AdminSectionHeader
            title={adminConsoleCopy.dashboard.charts.supportTitle}
            body={adminConsoleCopy.dashboard.charts.supportBody}
          />
          <div className="mt-6 space-y-6">
            <SimpleBarChart
              points={[
                {
                  label: adminConsoleCopy.common.support,
                  value: current.reaction_overview.support_count,
                },
                {
                  label: adminConsoleCopy.common.skip,
                  value: current.reaction_overview.skip_count,
                },
                {
                  label: adminConsoleCopy.common.moreLikeThis,
                  value: current.reaction_overview.more_like_this_count,
                },
                {
                  label: adminConsoleCopy.common.lessLikeThis,
                  value: current.reaction_overview.less_like_this_count,
                },
              ]}
              emptyLabel={adminConsoleCopy.common.noData}
              valueFormatter={formatCompactNumber}
            />
            <div>
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {adminConsoleCopy.dashboard.cards.supportActions}
              </p>
              <TrendChart
                points={supportTrendPoints}
                emptyLabel={adminConsoleCopy.common.noData}
                colorClassName="from-cyan-300 to-emerald-300"
              />
            </div>
          </div>
        </AdminSurface>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.96fr_1.04fr]">
        <AdminSurface>
          <AdminSectionHeader
            title={adminConsoleCopy.dashboard.charts.impactTitle}
            body={adminConsoleCopy.dashboard.charts.impactBody}
          />
          <div className="mt-6">
            <SimpleBarChart
              points={current.impact_distribution.map((bucket) => ({
                label: bucket.range_key,
                value: bucket.count,
              }))}
              emptyLabel={adminConsoleCopy.common.noData}
              valueFormatter={formatCompactNumber}
            />
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <div>
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {adminConsoleCopy.dashboard.charts.moderationTitle}
              </p>
              <DistributionList
                points={[
                  {
                    label: adminConsoleCopy.common.approved,
                    count: current.moderation_overview.approved_count,
                    share:
                      current.moderation_overview.approved_count /
                      Math.max(
                        current.moderation_overview.approved_count +
                          current.moderation_overview.rejected_count +
                          current.moderation_overview.needs_review_count +
                          current.moderation_overview.queued_count,
                        1,
                      ),
                  },
                  {
                    label: adminConsoleCopy.common.rejected,
                    count: current.moderation_overview.rejected_count,
                    share:
                      current.moderation_overview.rejected_count /
                      Math.max(
                        current.moderation_overview.approved_count +
                          current.moderation_overview.rejected_count +
                          current.moderation_overview.needs_review_count +
                          current.moderation_overview.queued_count,
                        1,
                      ),
                  },
                  {
                    label: adminConsoleCopy.common.manualReview,
                    count: current.moderation_overview.needs_review_count,
                    share:
                      current.moderation_overview.needs_review_count /
                      Math.max(
                        current.moderation_overview.approved_count +
                          current.moderation_overview.rejected_count +
                          current.moderation_overview.needs_review_count +
                          current.moderation_overview.queued_count,
                        1,
                      ),
                  },
                ]}
                emptyLabel={adminConsoleCopy.common.noData}
              />
            </div>
            <div>
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {adminConsoleCopy.dashboard.charts.duplicateTitle}
              </p>
              <DistributionList
                points={duplicateConcentration.data.map((item) => ({
                  label: item.label,
                  count: item.count,
                  share: item.share,
                }))}
                emptyLabel={adminConsoleCopy.common.noData}
              />
            </div>
            <div>
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {adminConsoleCopy.dashboard.charts.topAreasTitle}
              </p>
              <div className="space-y-3">
                {topAreas.data.length ? (
                  topAreas.data.map((area) => (
                    <article
                      key={area.area_key}
                      className="min-w-0 rounded-[1.25rem] border border-white/10 bg-white/5 p-4"
                    >
                      <div className="flex flex-col items-start gap-3">
                        <p className="break-words font-semibold text-white">{area.label}</p>
                        <AdminStatusBadge
                          label={area.dominant_category_slug ?? adminConsoleCopy.common.noData}
                          tone="subtle"
                        />
                      </div>
                      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-2 text-xs uppercase tracking-[0.18em] text-slate-400">
                        <span>{formatCompactNumber(area.issue_count)}</span>
                        <span>{area.average_impact_score.toFixed(1)}/10</span>
                        <span>{area.total_impact_score.toFixed(1)}</span>
                      </div>
                    </article>
                  ))
                ) : (
                  <p className="text-sm leading-6 text-slate-300">
                    {adminConsoleCopy.common.noData}
                  </p>
                )}
              </div>
            </div>
          </div>
        </AdminSurface>

        <AdminSurface>
          <AdminSectionHeader
            title={adminConsoleCopy.dashboard.charts.heatmapPreviewTitle}
            body={adminConsoleCopy.dashboard.charts.heatmapPreviewBody}
            action={
              <Button asChild variant="outline">
                <Link href={`/${locale}/admin/heatmap` as Route}>
                  {adminConsoleCopy.shell.sections.heatmap}
                </Link>
              </Button>
            }
          />
          <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-white/10">
            <IssueHeatmapMap
              points={current.heatmap_preview}
              issueCountLabel={adminConsoleCopy.heatmap.issueCount}
              secondaryLine={(point) =>
                "average_impact_score" in point && typeof point.average_impact_score === "number"
                  ? `${point.average_impact_score.toFixed(1)}/10`
                  : null
              }
              heightClassName="h-[420px]"
            />
          </div>
        </AdminSurface>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_0.92fr]">
        <AdminSurface>
          <AdminSectionHeader
            title={adminConsoleCopy.dashboard.charts.topPriorityTitle}
            body={adminConsoleCopy.dashboard.charts.topPriorityBody}
            action={
              <Button asChild variant="ghost">
                <Link href={`/${locale}/admin/issues` as Route}>
                  {adminConsoleCopy.common.openIssue}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            }
          />
          <div className="mt-6 grid gap-4">
            {current.top_priority_issues.map((issue) => (
              <Link
                key={issue.id}
                href={`/${locale}/admin/issues/${issue.id}` as Route}
                className="min-w-0 rounded-[1.4rem] border border-white/10 bg-white/5 p-4 transition-colors hover:bg-white/8"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <AdminStatusBadge
                    label={issue.category.display_name}
                    tone="primary"
                  />
                  <AdminStatusBadge
                    label={formatIssueStatus(issue.status)}
                    tone={formatStatusTone(issue.status)}
                  />
                </div>
                <h3 className="mt-3 font-display text-2xl font-semibold text-white">
                  {issue.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-slate-300">
                  {issue.short_description}
                </p>
                <AdminKeyValueGrid
                  columns={2}
                  items={[
                    {
                      label: adminConsoleCopy.heatmap.issueCount,
                      value: formatCompactNumber(issue.support_count),
                    },
                    {
                      label: adminConsoleCopy.heatmap.trustWeightedActivity,
                      value: issue.trust_weighted_support_total.toFixed(2),
                    },
                    {
                      label: adminConsoleCopy.heatmap.averageImpact,
                      value:
                        typeof issue.public_impact_score === "number"
                          ? `${issue.public_impact_score.toFixed(1)}/10`
                          : adminConsoleCopy.common.noData,
                    },
                    {
                      label: adminConsoleCopy.dashboard.cards.newThisWeek,
                      value: formatIssueDate(issue.created_at),
                    },
                  ]}
                />
              </Link>
            ))}
          </div>
        </AdminSurface>

        <div className="grid gap-6">
          <AdminSurface>
            <AdminSectionHeader
              title={adminConsoleCopy.dashboard.charts.recentTicketsTitle}
            />
            <div className="mt-6 space-y-3">
              {current.recent_tickets.length ? (
                current.recent_tickets.map((ticket) => (
                  <Link
                    key={ticket.id}
                    href={`/${locale}/admin/tickets/${ticket.id}` as Route}
                    className="block rounded-[1.25rem] border border-white/10 bg-white/5 p-4 transition-colors hover:bg-white/8"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <AdminStatusBadge label={ticket.type} tone="primary" />
                      <AdminStatusBadge
                        label={formatLifecycleLabel(ticket.status)}
                        tone={formatStatusTone(ticket.status)}
                      />
                    </div>
                    <p className="mt-3 font-semibold text-white">{ticket.subject}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {ticket.latest_message_preview ?? adminConsoleCopy.common.noData}
                    </p>
                    <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">
                      {ticket.latest_message_at
                        ? formatIssueDate(ticket.latest_message_at)
                        : formatIssueDate(ticket.updated_at)}
                    </p>
                  </Link>
                ))
              ) : (
                <p className="text-sm leading-6 text-slate-300">
                  {adminConsoleCopy.common.noData}
                </p>
              )}
            </div>
          </AdminSurface>

          <AdminSurface>
            <AdminSectionHeader
              title={adminConsoleCopy.dashboard.charts.recentModerationTitle}
            />
            <div className="mt-6 space-y-3">
              {current.recent_moderation.length ? (
                current.recent_moderation.map((issue) => (
                  <Link
                    key={issue.id}
                    href={`/${locale}/admin/moderation` as Route}
                    className="block rounded-[1.25rem] border border-white/10 bg-white/5 p-4 transition-colors hover:bg-white/8"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <AdminStatusBadge label={issue.category.display_name} tone="primary" />
                      {issue.latest_moderation ? (
                        <AdminStatusBadge
                          label={issue.latest_moderation.status}
                          tone={formatStatusTone(issue.latest_moderation.status)}
                        />
                      ) : null}
                    </div>
                    <p className="mt-3 font-semibold text-white">{issue.title}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {issue.latest_moderation?.summary ?? issue.short_description}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-3 text-xs uppercase tracking-[0.18em] text-slate-500">
                      <span>{formatIssueDate(issue.created_at)}</span>
                      <span>{issue.attachment_count}</span>
                      {issue.author ? (
                        <span>{issue.author.trust_weight_multiplier.toFixed(3)}</span>
                      ) : null}
                    </div>
                  </Link>
                ))
              ) : (
                <p className="text-sm leading-6 text-slate-300">
                  {adminConsoleCopy.common.noData}
                </p>
              )}
            </div>
          </AdminSurface>
        </div>
      </div>
    </section>
  );
}
