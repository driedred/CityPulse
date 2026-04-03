/* eslint-disable @next/next/no-img-element */

import { MapPin, MessageSquareText, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { appCopy } from "@/content/copy";
import type { PublicIssueSummary } from "@/lib/api/types";
import {
  formatAffectedPeopleEstimate,
  formatCompactNumber,
  formatImpactScore,
  formatIssueDate,
  getIssueLocationSnippet,
  getIssueSignalLabel,
} from "@/features/issues/lib/presenters";

type IssueCardProps = Readonly<{
  issue: PublicIssueSummary;
  onOpen: (issueId: string) => void;
  actions?: React.ReactNode;
  compact?: boolean;
}>;

export function IssueCard({ issue, onOpen, actions, compact = false }: IssueCardProps) {
  const signalLabel = getIssueSignalLabel(issue);

  return (
    <article className="overflow-hidden rounded-[1.75rem] border border-border/70 bg-card/85 shadow-soft backdrop-blur">
      <div className={compact ? "grid gap-4 p-4" : "grid gap-5 p-5 sm:p-6"}>
        <div className="overflow-hidden rounded-[1.5rem] border border-border/60 bg-muted/60">
          {issue.cover_image_url ? (
            <img
              src={issue.cover_image_url}
              alt={issue.title}
              className={compact ? "h-36 w-full object-cover" : "h-48 w-full object-cover"}
            />
          ) : (
            <div
              className={
                compact
                  ? "flex h-36 w-full flex-col justify-between bg-gradient-to-br from-secondary via-card to-accent/60 p-4"
                  : "flex h-48 w-full flex-col justify-between bg-gradient-to-br from-secondary via-card to-accent/60 p-5"
              }
            >
              <Badge variant="primary">{issue.category.display_name}</Badge>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                  {appCopy.issueViews.noImage}
                </p>
                <p className="mt-2 max-w-xs font-display text-xl font-semibold text-foreground">
                  {issue.title}
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="subtle">{issue.category.display_name}</Badge>
            <Badge variant="accent">{signalLabel}</Badge>
          </div>

          <div>
            <h3 className={compact ? "font-display text-xl font-semibold" : "font-display text-2xl font-semibold"}>
              {issue.title}
            </h3>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">
              {issue.short_description}
            </p>
          </div>

          <div className="grid gap-3 text-sm text-muted-foreground sm:grid-cols-2">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-primary" />
              <span>{getIssueLocationSnippet(issue)}</span>
            </div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>
                {appCopy.issueViews.impactLabel}: {formatImpactScore(issue.public_impact_score)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>
                {formatCompactNumber(issue.support_count)} {appCopy.issueViews.supportCountLabel}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>
                {appCopy.issueViews.affectedLabel}:{" "}
                {formatAffectedPeopleEstimate(issue.affected_people_estimate)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <MessageSquareText className="h-4 w-4 text-primary" />
              <span>{formatIssueDate(issue.created_at)}</span>
            </div>
            {typeof issue.distance_km === "number" ? (
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-primary" />
                <span>{issue.distance_km.toFixed(1)} km</span>
              </div>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" onClick={() => onOpen(issue.id)}>
              {appCopy.issueViews.openDetails}
            </Button>
            {actions}
          </div>
        </div>
      </div>
    </article>
  );
}
