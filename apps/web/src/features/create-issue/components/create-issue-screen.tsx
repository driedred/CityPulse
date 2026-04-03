/* eslint-disable @next/next/no-img-element */

"use client";

import type { Route } from "next";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { zodResolver } from "@hookform/resolvers/zod";
import { Camera, Sparkles, Upload, WandSparkles } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthRequiredCard } from "@/components/auth/auth-required-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { InlineMessage } from "@/components/ui/inline-message";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { appCopy } from "@/content/copy";
import { LocationPickerMap } from "@/features/create-issue/components/location-picker-map";
import { IssueCard } from "@/features/issues/components/issue-card";
import { IssueDetailsSheet } from "@/features/issues/components/issue-details-sheet";
import { useIssueCategories } from "@/features/issues/hooks/use-public-issues";
import {
  formatAffectedPeopleEstimate,
  formatCoordinates,
  formatImpactScore,
  getIssueLocationSnippet,
} from "@/features/issues/lib/presenters";
import { useUserLocation } from "@/hooks/use-user-location";
import { apiClient } from "@/lib/api/client";
import type {
  DuplicateLookupStatus,
  DuplicateSuggestion,
  Issue,
  RewriteResponse,
} from "@/lib/api/types";
import { useAuth } from "@/lib/auth/auth-provider";

const createIssueSchema = z.object({
  title: z.string().trim().min(4, "Enter a short title.").max(160),
  short_description: z
    .string()
    .trim()
    .min(10, "Add a clearer description.")
    .max(4000),
  category_id: z.string().min(1, "Choose a category."),
});

type CreateIssueValues = z.infer<typeof createIssueSchema>;

type PhotoDraft = {
  id: string;
  file: File;
  previewUrl: string;
};

type CreateIssueScreenProps = Readonly<{
  locale: string;
}>;

const STEP_LABELS = [
  appCopy.create.stepContent,
  appCopy.create.stepLocation,
  appCopy.create.stepReview,
] as const;

function sanitizeFileName(fileName: string) {
  return fileName.replace(/[^a-zA-Z0-9._-]+/g, "-").toLowerCase();
}

function createStorageKey(issueId: string, fileName: string) {
  const randomPart =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}`;
  return `issues/${issueId}/${randomPart}-${sanitizeFileName(fileName)}`;
}

function getSubmittedIssueFeedback(issue: Issue) {
  const explanation =
    issue.latest_moderation?.user_safe_explanation ??
    issue.latest_moderation?.summary ??
    appCopy.create.successBody;

  if (issue.status === "rejected") {
    return {
      variant: "error" as const,
      title: appCopy.create.moderationRejectedTitle,
      body: explanation || appCopy.create.moderationRejectedBody,
    };
  }

  if (
    issue.moderation_state === "under_review" ||
    issue.latest_moderation?.status === "needs_review"
  ) {
    return {
      variant: "warning" as const,
      title: appCopy.create.moderationReviewTitle,
      body: explanation || appCopy.create.moderationReviewBody,
    };
  }

  return {
    variant: "success" as const,
    title: appCopy.create.moderationApprovedTitle,
    body: explanation || appCopy.create.moderationApprovedBody,
  };
}

export function CreateIssueScreen({ locale }: CreateIssueScreenProps) {
  const [step, setStep] = useState(0);
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [photoDrafts, setPhotoDrafts] = useState<PhotoDraft[]>([]);
  const [rewriteSuggestion, setRewriteSuggestion] = useState<RewriteResponse | null>(null);
  const [duplicateMatches, setDuplicateMatches] = useState<DuplicateSuggestion[]>([]);
  const [duplicateStatus, setDuplicateStatus] =
    useState<DuplicateLookupStatus>("no_match");
  const [isCheckingDuplicates, setIsCheckingDuplicates] = useState(false);
  const [isRewriting, setIsRewriting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [submittedIssue, setSubmittedIssue] = useState<Issue | null>(null);
  const [supportedDuplicateId, setSupportedDuplicateId] = useState<string | null>(null);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const { token, user } = useAuth();
  const categories = useIssueCategories();
  const { location, isLoading: isLocating, error: locationError, requestLocation } =
    useUserLocation();
  const form = useForm<CreateIssueValues>({
    resolver: zodResolver(createIssueSchema),
    defaultValues: {
      title: "",
      short_description: "",
      category_id: "",
    },
  });
  const photoDraftsRef = useRef<PhotoDraft[]>([]);

  useEffect(() => {
    photoDraftsRef.current = photoDrafts;
  }, [photoDrafts]);

  useEffect(() => {
    return () => {
      photoDraftsRef.current.forEach((draft) => URL.revokeObjectURL(draft.previewUrl));
    };
  }, []);

  if (!user || !token) {
    return <AuthRequiredCard locale={locale} />;
  }

  const authToken = token;

  if (submittedIssue) {
    const submissionFeedback = getSubmittedIssueFeedback(submittedIssue);

    return (
      <section className="space-y-6">
        <div className="rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-primary">
            {appCopy.create.moderationFeedbackHeading}
          </p>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight">
            {submissionFeedback.title}
          </h1>
          <p className="mt-4 text-sm leading-7 text-muted-foreground">
            {submissionFeedback.body}
          </p>
        </div>

        <InlineMessage variant={submissionFeedback.variant}>
          {submissionFeedback.title} {submissionFeedback.body}
        </InlineMessage>

        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href={`/${locale}/my-issues` as Route}>{appCopy.create.goToMyIssues}</Link>
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setSubmittedIssue(null);
              setNotice(null);
            }}
          >
            {appCopy.create.createAnother}
          </Button>
        </div>
      </section>
    );
  }

  const values = form.watch();
  const isLocationValid =
    typeof latitude === "number" &&
    Number.isFinite(latitude) &&
    typeof longitude === "number" &&
    Number.isFinite(longitude);

  function resetFlow() {
    form.reset({
      title: "",
      short_description: "",
      category_id: "",
    });
    setLatitude(null);
    setLongitude(null);
    setPhotoDrafts((current) => {
      current.forEach((draft) => URL.revokeObjectURL(draft.previewUrl));
      return [];
    });
    setRewriteSuggestion(null);
    setDuplicateMatches([]);
    setDuplicateStatus("no_match");
    setSupportedDuplicateId(null);
    setStep(0);
  }

  function handlePhotoSelection(files: FileList | null) {
    if (!files?.length) {
      return;
    }

    const nextDrafts = Array.from(files).map((file) => ({
      id:
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${file.name}`,
      file,
      previewUrl: URL.createObjectURL(file),
    }));

    setPhotoDrafts((current) => [...current, ...nextDrafts]);
  }

  function removePhoto(draftId: string) {
    setPhotoDrafts((current) => {
      const draft = current.find((item) => item.id === draftId);
      if (draft) {
        URL.revokeObjectURL(draft.previewUrl);
      }
      return current.filter((item) => item.id !== draftId);
    });
  }

  async function runRewrite() {
    const valid = await form.trigger(["title", "short_description"]);
    if (!valid) {
      setNotice(appCopy.create.rewriteNoChanges);
      return;
    }

    setIsRewriting(true);
    setNotice(null);

    try {
      const response = await apiClient.rewriteIssueText({
        title: form.getValues("title"),
        short_description: form.getValues("short_description"),
        category_id: form.getValues("category_id") || null,
        source_locale: locale,
        context_hint:
          categories.data.find((category) => category.id === form.getValues("category_id"))
            ?.display_name ?? null,
      });
      setRewriteSuggestion(response);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : appCopy.issueViews.errorTitle);
    } finally {
      setIsRewriting(false);
    }
  }

  function applyRewrite() {
    if (!rewriteSuggestion) {
      return;
    }

    form.setValue("title", rewriteSuggestion.rewritten_title, {
      shouldDirty: true,
      shouldValidate: true,
    });
    form.setValue("short_description", rewriteSuggestion.rewritten_description, {
      shouldDirty: true,
      shouldValidate: true,
    });
    setRewriteSuggestion(null);
    setNotice(appCopy.create.rewriteSaved);
  }

  async function checkDuplicates() {
    const valid = await form.trigger();
    if (!valid || !isLocationValid) {
      setNotice(appCopy.create.validationTitle);
      return false;
    }

    setIsCheckingDuplicates(true);
    setNotice(null);

    try {
      const response = await apiClient.suggestDuplicates({
        title: form.getValues("title"),
        short_description: form.getValues("short_description"),
        category_id: form.getValues("category_id") || null,
        latitude: latitude as number,
        longitude: longitude as number,
      });
      setDuplicateStatus(response.status);
      setDuplicateMatches(response.matches);
      return true;
    } catch (error) {
      setNotice(error instanceof Error ? error.message : appCopy.issueViews.errorTitle);
      return false;
    } finally {
      setIsCheckingDuplicates(false);
    }
  }

  async function goToLocationStep() {
    const valid = await form.trigger();
    if (!valid) {
      setNotice(appCopy.create.validationTitle);
      return;
    }

    setNotice(null);
    setStep(1);
  }

  async function goToReviewStep() {
    if (!isLocationValid) {
      setNotice(appCopy.create.validationTitle);
      return;
    }

    const checked = await checkDuplicates();
    if (checked) {
      setStep(2);
    }
  }

  async function supportExistingIssue(match: DuplicateSuggestion) {
    try {
      const response = await apiClient.supportExistingIssue(authToken, match.existing_issue_id, {
        candidate_title: form.getValues("title"),
        candidate_description: form.getValues("short_description"),
        candidate_category_id: form.getValues("category_id") || null,
        candidate_latitude: latitude,
        candidate_longitude: longitude,
        similarity_score: match.similarity_score,
        distance_km: match.distance_km,
        text_similarity: match.text_similarity,
        category_match: match.category_match,
        reason_breakdown: match.reason_breakdown,
        image_hashes: [],
      });
      setSupportedDuplicateId(match.existing_issue_id);
      setNotice([
        appCopy.create.duplicateSupportResult,
        formatImpactScore(response.public_impact_score),
        formatAffectedPeopleEstimate(response.affected_people_estimate),
      ].join(" | "));
      /* setNotice(
        `${appCopy.create.duplicateSupportResult} ${response.public_impact_score.toFixed(1)}/10 · ${response.affected_people_estimate}`,
      ); */
    } catch (error) {
      setNotice(error instanceof Error ? error.message : appCopy.issueViews.errorTitle);
    }
  }

  async function submitIssue() {
    const valid = await form.trigger();
    if (!valid || !isLocationValid) {
      setNotice(appCopy.create.validationTitle);
      return;
    }

    setIsSubmitting(true);
    setNotice(null);

    try {
      const createdIssue = await apiClient.submitIssue(authToken, {
        title: form.getValues("title"),
        short_description: form.getValues("short_description"),
        category_id: form.getValues("category_id"),
        latitude: latitude as number,
        longitude: longitude as number,
        source_locale: locale,
      });

      for (const photo of photoDrafts) {
        await apiClient.createAttachmentMetadata(authToken, createdIssue.id, {
          original_filename: photo.file.name,
          content_type: photo.file.type || "application/octet-stream",
          size_bytes: photo.file.size,
          storage_key: createStorageKey(createdIssue.id, photo.file.name),
        });
      }

      setSubmittedIssue(createdIssue);
      resetFlow();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : appCopy.issueViews.errorTitle);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function useCurrentLocation() {
    const currentLocation = await requestLocation();
    if (!currentLocation) {
      setNotice(locationError || appCopy.create.locationError);
      return;
    }

    setLatitude(currentLocation.latitude);
    setLongitude(currentLocation.longitude);
  }

  return (
    <section className="space-y-6">
      <div className="rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-primary">
              {STEP_LABELS[step]}
            </p>
            <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight">
              {appCopy.create.title}
            </h1>
            <p className="mt-4 text-sm leading-7 text-muted-foreground">
              {appCopy.create.subtitle}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {STEP_LABELS.map((label, index) => (
              <Badge key={label} variant={index === step ? "primary" : "subtle"}>
                {index + 1}. {label}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {notice ? (
        <InlineMessage variant="info">{notice}</InlineMessage>
      ) : null}

      {step === 0 ? (
        <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <form className="space-y-5 rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
            <Field label={appCopy.create.titleLabel} error={form.formState.errors.title?.message}>
              <Input
                placeholder={appCopy.create.titlePlaceholder}
                {...form.register("title")}
              />
            </Field>
            <Field
              label={appCopy.create.descriptionLabel}
              error={form.formState.errors.short_description?.message}
            >
              <Textarea
                placeholder={appCopy.create.descriptionPlaceholder}
                {...form.register("short_description")}
              />
            </Field>
            <Field
              label={appCopy.create.categoryLabel}
              error={form.formState.errors.category_id?.message}
            >
              <Select {...form.register("category_id")}>
                <option value="">{appCopy.create.categoryPlaceholder}</option>
                {categories.data.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.display_name}
                  </option>
                ))}
              </Select>
            </Field>

            <div className="rounded-[1.5rem] border border-border/70 bg-background/70 p-4">
              <div className="flex items-center gap-2">
                <Camera className="h-4 w-4 text-primary" />
                <p className="text-sm font-semibold">{appCopy.create.photoLabel}</p>
              </div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {appCopy.create.photoHint}
              </p>
              <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-full border border-border/70 bg-card px-4 py-2 text-sm font-semibold text-foreground">
                <Upload className="h-4 w-4" />
                <span>{appCopy.create.photoAction}</span>
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  className="sr-only"
                  onChange={(event) => handlePhotoSelection(event.target.files)}
                />
              </label>

              {photoDrafts.length ? (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {photoDrafts.map((draft) => (
                    <div
                      key={draft.id}
                      className="overflow-hidden rounded-[1.25rem] border border-border/70 bg-card"
                    >
                      <img src={draft.previewUrl} alt={draft.file.name} className="h-32 w-full object-cover" />
                      <div className="space-y-2 p-3">
                        <p className="truncate text-sm font-semibold">{draft.file.name}</p>
                        <button
                          type="button"
                          className="text-sm font-semibold text-primary"
                          onClick={() => removePhoto(draft.id)}
                        >
                          {appCopy.create.removePhoto}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">{appCopy.create.photoEmpty}</p>
              )}
            </div>

            <div className="flex flex-wrap gap-3">
              <Button type="button" variant="outline" onClick={runRewrite} disabled={isRewriting}>
                <WandSparkles className="mr-2 h-4 w-4" />
                {isRewriting ? appCopy.common.loading : appCopy.create.rewriteAction}
              </Button>
              <Button type="button" onClick={goToLocationStep}>
                {appCopy.create.next}
              </Button>
            </div>
          </form>

          <div className="space-y-5">
            <div className="rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <p className="text-sm font-semibold">{appCopy.create.rewriteHeading}</p>
              </div>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                {appCopy.create.rewriteBody}
              </p>

              {rewriteSuggestion ? (
                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-[1.5rem] border border-border/70 bg-background/70 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                      {appCopy.common.overview}
                    </p>
                    <p className="mt-3 font-semibold">{values.title}</p>
                    <p className="mt-3 text-sm leading-6 text-muted-foreground">
                      {values.short_description}
                    </p>
                  </div>
                  <div className="rounded-[1.5rem] border border-primary/20 bg-primary/5 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">
                      {appCopy.create.rewriteAction}
                    </p>
                    <p className="mt-3 font-semibold">{rewriteSuggestion.rewritten_title}</p>
                    <p className="mt-3 text-sm leading-6 text-muted-foreground">
                      {rewriteSuggestion.rewritten_description}
                    </p>
                    <div className="mt-4 space-y-2 text-sm text-muted-foreground">
                      <p>
                        <span className="font-semibold text-foreground">
                          {appCopy.create.rewriteExplanationLabel}:
                        </span>{" "}
                        {rewriteSuggestion.explanation}
                      </p>
                      {rewriteSuggestion.tone_classification ? (
                        <p>
                          <span className="font-semibold text-foreground">
                            {appCopy.create.rewriteToneLabel}:
                          </span>{" "}
                          {rewriteSuggestion.tone_classification}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="mt-5 text-sm text-muted-foreground">{appCopy.create.rewriteBody}</p>
              )}

              {rewriteSuggestion ? (
                <div className="mt-5 flex flex-wrap gap-3">
                  <Button type="button" onClick={applyRewrite}>
                    {appCopy.create.acceptRewrite}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => setRewriteSuggestion(null)}>
                    {appCopy.create.rejectRewrite}
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {step === 1 ? (
        <div className="grid gap-6 xl:grid-cols-[1.18fr_0.82fr]">
          <div className="rounded-[2rem] border border-border/70 bg-card/80 p-4 shadow-soft backdrop-blur sm:p-5">
            <LocationPickerMap
              latitude={latitude}
              longitude={longitude}
              userLocation={location}
              onSelectLocation={(coordinates) => {
                setLatitude(coordinates.latitude);
                setLongitude(coordinates.longitude);
              }}
            />
          </div>

          <div className="space-y-5">
            <div className="rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">
                {appCopy.create.locationHeading}
              </p>
              <p className="mt-4 text-sm leading-7 text-muted-foreground">
                {appCopy.create.locationBody}
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Button type="button" variant="outline" onClick={useCurrentLocation}>
                  {isLocating ? appCopy.common.loading : appCopy.create.useMyLocation}
                </Button>
                <Button type="button" variant="ghost" onClick={() => setStep(0)}>
                  {appCopy.create.back}
                </Button>
                <Button type="button" onClick={goToReviewStep}>
                  {appCopy.create.next}
                </Button>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={appCopy.create.latitudeLabel}>
                <Input
                  type="number"
                  step="any"
                  value={latitude ?? ""}
                  onChange={(event) =>
                    setLatitude(
                      event.target.value ? Number(event.target.value) : null,
                    )
                  }
                />
              </Field>
              <Field label={appCopy.create.longitudeLabel}>
                <Input
                  type="number"
                  step="any"
                  value={longitude ?? ""}
                  onChange={(event) =>
                    setLongitude(
                      event.target.value ? Number(event.target.value) : null,
                    )
                  }
                />
              </Field>
            </div>

            {locationError ? (
              <InlineMessage variant="warning">{locationError}</InlineMessage>
            ) : null}
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-5">
            <div className="rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">
                {appCopy.create.reviewHeading}
              </p>
              <p className="mt-4 text-sm leading-7 text-muted-foreground">
                {appCopy.create.reviewBody}
              </p>

              <div className="mt-6 rounded-[1.5rem] border border-border/70 bg-background/70 p-5">
                <p className="text-sm font-semibold">{appCopy.create.submissionSummary}</p>
                <div className="mt-4 space-y-3 text-sm text-muted-foreground">
                  <p>{values.title}</p>
                  <p>{values.short_description}</p>
                  <p>
                    {categories.data.find((category) => category.id === values.category_id)
                      ?.display_name ?? appCopy.common.none}
                  </p>
                  <p>
                    {isLocationValid
                      ? formatCoordinates(latitude as number, longitude as number)
                      : appCopy.common.none}
                  </p>
                  <p>
                    {photoDrafts.length} {appCopy.create.photoLabel}
                  </p>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                <Button type="button" variant="ghost" onClick={() => setStep(1)}>
                  {appCopy.create.back}
                </Button>
                <Button type="button" variant="outline" onClick={checkDuplicates}>
                  {isCheckingDuplicates
                    ? appCopy.common.loading
                    : appCopy.create.checkDuplicates}
                </Button>
                <Button type="button" onClick={submitIssue} disabled={isSubmitting}>
                  {isSubmitting
                    ? appCopy.common.loading
                    : duplicateStatus === "no_match"
                      ? appCopy.create.submit
                      : appCopy.create.submitAnyway}
                </Button>
              </div>
            </div>

            <div className="rounded-[2rem] border border-amber-400/25 bg-amber-400/10 p-6 shadow-soft backdrop-blur sm:p-8">
              <p className="text-sm font-semibold">{appCopy.create.duplicateHeading}</p>
              <p className="mt-3 text-sm leading-7 text-amber-950/80 dark:text-amber-100/90">
                {duplicateStatus === "high_confidence_duplicate"
                  ? appCopy.create.duplicateHighConfidence
                  : duplicateStatus === "possible_duplicates"
                    ? appCopy.create.duplicatePossible
                    : appCopy.create.duplicateBody}
              </p>
            </div>

            {duplicateMatches.length ? (
              <div className="grid gap-4">
                {duplicateMatches.map((match) => (
                  <div key={match.existing_issue_id} className="space-y-3">
                    <IssueCard
                      issue={match.issue}
                      compact
                      onOpen={setSelectedIssueId}
                      actions={
                        <Button
                          type="button"
                          variant={
                            supportedDuplicateId === match.existing_issue_id
                              ? "secondary"
                              : match.recommended_action === "support_existing"
                                ? "default"
                                : "outline"
                          }
                          onClick={() => supportExistingIssue(match)}
                        >
                          {match.recommended_action === "support_existing"
                            ? appCopy.create.supportExistingFaster
                            : appCopy.create.supportExisting}
                        </Button>
                      }
                    />
                    <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <Badge
                        variant={
                          match.recommended_action === "support_existing"
                            ? "primary"
                            : "subtle"
                        }
                      >
                        {match.recommended_action === "support_existing"
                          ? appCopy.common.supportRecommended
                          : appCopy.common.reviewRecommended}
                      </Badge>
                      <span>{match.reason_breakdown.join(" | ")}</span>
                      <span>{match.similarity_score.toFixed(2)}</span>
                      {/*
                      {match.reason} · {match.similarity_score.toFixed(2)}
                      */}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <InlineMessage variant="success">{appCopy.create.noDuplicates}</InlineMessage>
            )}
          </div>

          <div className="space-y-5">
            <div className="rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
              <p className="text-sm font-semibold">{appCopy.create.photoLabel}</p>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">
                {appCopy.create.metadataPending}
              </p>
              <div className="mt-4 space-y-3">
                {photoDrafts.length ? (
                  photoDrafts.map((draft) => (
                    <div
                      key={draft.id}
                      className="flex items-center gap-3 rounded-[1.25rem] border border-border/70 bg-background/70 p-3"
                    >
                      <img src={draft.previewUrl} alt={draft.file.name} className="h-16 w-16 rounded-2xl object-cover" />
                      <div>
                        <p className="text-sm font-semibold">{draft.file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {Math.round(draft.file.size / 1024)} KB
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">{appCopy.create.photoEmpty}</p>
                )}
              </div>
            </div>

            <div className="rounded-[2rem] border border-border/70 bg-card/80 p-6 shadow-soft backdrop-blur sm:p-8">
              <p className="text-sm font-semibold">{appCopy.common.location}</p>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">
                {isLocationValid
                  ? getIssueLocationSnippet({
                      location_snippet: "",
                      latitude: latitude as number,
                      longitude: longitude as number,
                    })
                  : appCopy.common.none}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {isLocationValid
                  ? formatCoordinates(latitude as number, longitude as number)
                  : appCopy.common.none}
              </p>
            </div>
          </div>
        </div>
      ) : null}
      <IssueDetailsSheet
        locale={locale}
        issueId={selectedIssueId}
        isOpen={Boolean(selectedIssueId)}
        onClose={() => setSelectedIssueId(null)}
      />
    </section>
  );
}
