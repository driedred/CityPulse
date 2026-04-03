/* eslint-disable @next/next/no-img-element */

import type { Route } from "next";
import Link from "next/link";

import { CalendarClock, Languages, MapPin, Paperclip, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { appCopy } from "@/content/copy";
import type { PublicIssueDetail } from "@/lib/api/types";
import {
  formatAffectedPeopleEstimate,
  formatCompactNumber,
  formatCoordinates,
  formatImpactScore,
  formatIssueDate,
  getIssueLocationSnippet,
  getIssueSignalLabel,
} from "@/features/issues/lib/presenters";

type IssueDetailsContentProps = Readonly<{
  issue: PublicIssueDetail;
  locale: string;
  onSupport?: () => void;
  isSupporting?: boolean;
}>;

export function IssueDetailsContent({
  issue,
  locale,
  onSupport,
  isSupporting = false,
}: IssueDetailsContentProps) {
  const signalLabel = getIssueSignalLabel(issue);

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-[1.5rem] border border-border/70 bg-muted/60">
        {issue.cover_image_url ? (
          <img src={issue.cover_image_url} alt={issue.title} className="h-56 w-full object-cover" />
        ) : (
          <div className="flex h-56 flex-col justify-between bg-gradient-to-br from-secondary via-card to-accent/60 p-6">
            <Badge variant="primary">{issue.category.display_name}</Badge>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                {appCopy.issueViews.noImage}
              </p>
              <p className="mt-2 max-w-md font-display text-3xl font-semibold text-foreground">
                {issue.title}
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="subtle">{issue.category.display_name}</Badge>
        <Badge variant="accent">{signalLabel}</Badge>
      </div>

      <div>
        <h2 className="font-display text-3xl font-semibold">{issue.title}</h2>
        <p className="mt-4 text-sm leading-7 text-muted-foreground">{issue.short_description}</p>
      </div>

      <div className="grid gap-4 rounded-[1.5rem] border border-border/70 bg-card/70 p-5 sm:grid-cols-2">
        <div className="flex items-start gap-3">
          <MapPin className="mt-1 h-4 w-4 text-primary" />
          <div>
            <p className="text-sm font-semibold">{appCopy.issueDetail.locationTitle}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {getIssueLocationSnippet(issue)}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {formatCoordinates(issue.latitude, issue.longitude)}
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Sparkles className="mt-1 h-4 w-4 text-primary" />
          <div>
            <p className="text-sm font-semibold">{appCopy.issueDetail.scoreTitle}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {formatImpactScore(issue.public_impact_score)} · {signalLabel}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {formatAffectedPeopleEstimate(issue.affected_people_estimate)}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {formatCompactNumber(issue.support_count)} {appCopy.issueViews.supportCountLabel}
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Languages className="mt-1 h-4 w-4 text-primary" />
          <div>
            <p className="text-sm font-semibold">{appCopy.issueDetail.localeLabel}</p>
            <p className="mt-1 text-sm text-muted-foreground">{issue.source_locale}</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <CalendarClock className="mt-1 h-4 w-4 text-primary" />
          <div>
            <p className="text-sm font-semibold">{appCopy.issueDetail.createdLabel}</p>
            <p className="mt-1 text-sm text-muted-foreground">{formatIssueDate(issue.created_at)}</p>
          </div>
        </div>
      </div>

      <div className="rounded-[1.5rem] border border-border/70 bg-card/70 p-5">
        <div className="flex items-center gap-2">
          <Paperclip className="h-4 w-4 text-primary" />
          <p className="text-sm font-semibold">{appCopy.issueDetail.attachmentsTitle}</p>
        </div>
        <div className="mt-4 space-y-3">
          {issue.attachments.length ? (
            issue.attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="rounded-[1.25rem] border border-border/70 bg-background/70 px-4 py-3 text-sm text-muted-foreground"
              >
                <p className="font-semibold text-foreground">{attachment.original_filename}</p>
                <p className="mt-1">
                  {attachment.content_type} · {Math.round(attachment.size_bytes / 1024)} KB
                </p>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">{appCopy.common.none}</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {onSupport ? (
          <Button type="button" onClick={onSupport} disabled={isSupporting}>
            {isSupporting ? appCopy.common.loading : appCopy.issueDetail.supportAction}
          </Button>
        ) : null}
        <Button asChild variant="outline">
          <Link href={`/${locale}/issues/${issue.id}` as Route}>
            {appCopy.issueDetail.viewPage}
          </Link>
        </Button>
      </div>
    </div>
  );
}
