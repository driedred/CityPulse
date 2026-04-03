"use client";

import type { Route } from "next";
import Link from "next/link";

import { ArrowUpRight, MapPin, Paperclip, Sparkles } from "lucide-react";

import { AuthRequiredCard } from "@/components/auth/auth-required-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineMessage } from "@/components/ui/inline-message";
import { PageLoading } from "@/components/ui/page-loading";
import { appCopy } from "@/content/copy";
import { useMyIssues } from "@/features/my-issues/hooks/use-my-issues";
import {
  formatCompactNumber,
  formatIssueDate,
  formatModerationDecision,
  formatModerationLayer,
  formatIssueStatus,
  getIssueLocationSnippet,
} from "@/features/issues/lib/presenters";
import { useAuth } from "@/lib/auth/auth-provider";

type MyIssuesScreenProps = Readonly<{
  locale: string;
}>;

export function MyIssuesScreen({ locale }: MyIssuesScreenProps) {
  const { token, user } = useAuth();
  const issues = useMyIssues(token);

  if (!user) {
    return <AuthRequiredCard locale={locale} />;
  }

  return (
    <section className="space-y-6">
      <div className="rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-primary">
              {appCopy.myIssues.draftLabel}
            </p>
            <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight">
              {appCopy.myIssues.title}
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-muted-foreground">
              {appCopy.myIssues.subtitle}
            </p>
          </div>

          <Button asChild>
            <Link href={`/${locale}/create` as Route}>{appCopy.myIssues.createAction}</Link>
          </Button>
        </div>
      </div>

      {issues.error ? (
        <InlineMessage variant="error">{issues.error}</InlineMessage>
      ) : null}

      {issues.isLoading ? (
        <PageLoading title={appCopy.common.loading} />
      ) : issues.data.length ? (
        <div className="grid gap-5 xl:grid-cols-2">
          {issues.data.map((issue) => (
            <article
              key={issue.id}
              className="rounded-[1.75rem] border border-border/70 bg-card/85 p-5 shadow-soft backdrop-blur sm:p-6"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="subtle">{issue.category.display_name}</Badge>
                <Badge variant="primary">{formatIssueStatus(issue.status)}</Badge>
                {issue.latest_moderation ? (
                  <Badge variant="accent">
                    {formatModerationLayer(issue.latest_moderation.layer)} ·{" "}
                    {formatModerationDecision(issue.latest_moderation)}
                  </Badge>
                ) : null}
              </div>

              <div className="mt-4">
                <h2 className="font-display text-2xl font-semibold">{issue.title}</h2>
                <p className="mt-3 text-sm leading-7 text-muted-foreground">
                  {issue.short_description}
                </p>
              </div>

              <div className="mt-5 grid gap-3 text-sm text-muted-foreground sm:grid-cols-2">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-primary" />
                  <span>{getIssueLocationSnippet(issue)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span>
                    {formatCompactNumber(issue.support_count)} {appCopy.myIssues.supportLabel}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Paperclip className="h-4 w-4 text-primary" />
                  <span>
                    {issue.attachments.length} {appCopy.common.attachments}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <ArrowUpRight className="h-4 w-4 text-primary" />
                  <span>{formatIssueDate(issue.created_at)}</span>
                </div>
              </div>

              {issue.latest_moderation?.user_safe_explanation ? (
                <div className="mt-5 rounded-[1.25rem] border border-border/70 bg-background/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">
                    {appCopy.myIssues.moderationLabel}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {issue.latest_moderation.user_safe_explanation}
                  </p>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          title={appCopy.myIssues.emptyTitle}
          body={appCopy.myIssues.emptyBody}
          action={
            <Button asChild>
              <Link href={`/${locale}/create` as Route}>{appCopy.myIssues.createAction}</Link>
            </Button>
          }
        />
      )}
    </section>
  );
}
