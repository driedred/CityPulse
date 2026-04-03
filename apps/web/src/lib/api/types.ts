export type UserRole = "citizen" | "admin";

export type IssueStatus =
  | "draft"
  | "pending_moderation"
  | "approved"
  | "rejected"
  | "published"
  | "archived";

export type ModerationState =
  | "not_requested"
  | "queued"
  | "under_review"
  | "completed";
export type ModerationLayer = "deterministic" | "llm";
export type AbuseRiskLevel = "low" | "medium" | "high";
export type IntegrityEventSeverity = "low" | "medium" | "high";
export type ModerationResultStatus =
  | "queued"
  | "approved"
  | "needs_review"
  | "rejected";

export type SwipeAction =
  | "support"
  | "skip"
  | "more_like_this"
  | "less_like_this";

export type PublicIssueSort = "top" | "recent" | "nearby";
export type DuplicateLookupStatus =
  | "no_match"
  | "possible_duplicates"
  | "high_confidence_duplicate";
export type DuplicateRecommendedAction =
  | "support_existing"
  | "review_before_submit"
  | "submit_new_issue";
export type RewriteToneClassification =
  | "constructive"
  | "neutral"
  | "frustrated"
  | "accusatory"
  | "rage"
  | "low_signal";

export type ApiErrorPayload = {
  error: {
    code: string;
    message: string;
    details?: unknown;
    request_id?: string | null;
  };
};

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  preferred_locale: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminUserIdentity = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  preferred_locale: string;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
};

export type IntegrityFactor = {
  name: string;
  label: string;
  effect: "positive" | "negative" | "risk";
  signal: number | null;
  points: number | null;
  details: Record<string, unknown>;
};

export type IntegrityEvent = {
  id: string;
  event_type: string;
  severity: IntegrityEventSeverity;
  entity_type: string | null;
  entity_id: string | null;
  summary: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type UserIntegrityCompact = {
  user: AdminUserIdentity;
  trust_score: number;
  trust_weight_multiplier: number;
  abuse_risk_level: AbuseRiskLevel;
  abuse_risk_score: number;
  sanction_count: number;
  summary: string | null;
  updated_at: string;
};

export type UserIntegritySummary = UserIntegrityCompact & {
  trust_factors: IntegrityFactor[];
  abuse_factors: IntegrityFactor[];
  recommended_actions: string[];
  metrics: Record<string, unknown>;
};

export type UserIntegrityDetail = UserIntegritySummary & {
  recent_events: IntegrityEvent[];
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type IssueCategory = {
  id: string;
  slug: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
  severity_baseline: number;
  affected_people_baseline: number;
};

export type IssueAttachment = {
  id: string;
  issue_id: string;
  uploader_id: string;
  storage_key: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
};

export type ModerationReason = {
  code: string;
  label: string;
  severity: "low" | "medium" | "high";
  evidence: string | null;
};

export type IssueModerationSummary = {
  id: string;
  layer: ModerationLayer;
  status: ModerationResultStatus;
  decision_code: string;
  provider_name: string | null;
  model_name: string | null;
  confidence: number | null;
  summary: string | null;
  user_safe_explanation: string | null;
  escalation_required: boolean;
  machine_reasons: ModerationReason[];
  normalized_category_slug: string | null;
  created_at: string;
};

export type IssueModerationAdmin = IssueModerationSummary & {
  internal_notes: string | null;
  flags: Record<string, unknown>;
};

export type IssueModerationAudit = {
  issue_id: string;
  author: UserIntegrityCompact | null;
  issue_status: IssueStatus;
  moderation_state: ModerationState;
  latest_result: IssueModerationSummary | null;
  results: IssueModerationAdmin[];
};

export type AdminModerationIssue = {
  id: string;
  author: UserIntegrityCompact | null;
  title: string;
  short_description: string;
  source_locale: string;
  status: IssueStatus;
  moderation_state: ModerationState;
  category: IssueCategory;
  created_at: string;
  updated_at: string;
  attachment_count: number;
  latest_moderation: IssueModerationSummary | null;
};

export type PublicIssueSummary = {
  id: string;
  title: string;
  short_description: string;
  latitude: number;
  longitude: number;
  category: IssueCategory;
  location_snippet: string;
  support_count: number;
  public_impact_score: number | null;
  affected_people_estimate: number | null;
  importance_label: string | null;
  cover_image_url: string | null;
  created_at: string;
  updated_at: string;
  distance_km: number | null;
};

export type PublicIssueDetail = {
  id: string;
  title: string;
  short_description: string;
  latitude: number;
  longitude: number;
  category: IssueCategory;
  location_snippet: string;
  support_count: number;
  public_impact_score: number | null;
  affected_people_estimate: number | null;
  importance_label: string | null;
  cover_image_url: string | null;
  source_locale: string;
  attachments: IssueAttachment[];
  created_at: string;
  updated_at: string;
};

export type Issue = {
  id: string;
  author_id: string;
  title: string;
  short_description: string;
  latitude: number;
  longitude: number;
  status: IssueStatus;
  moderation_state: ModerationState;
  source_locale: string;
  category: IssueCategory;
  attachments: IssueAttachment[];
  support_count: number;
  location_snippet: string;
  public_impact_score: number | null;
  affected_people_estimate: number | null;
  latest_moderation: IssueModerationSummary | null;
  created_at: string;
  updated_at: string;
};

export type PublicIssueMapMarker = {
  id: string;
  title: string;
  latitude: number;
  longitude: number;
  category: IssueCategory;
  location_snippet: string;
  support_count: number;
  public_impact_score: number | null;
  affected_people_estimate: number | null;
  importance_label: string | null;
};

export type IssuePublicImpact = {
  issue_id: string;
  public_impact_score: number;
  affected_people_estimate: number;
  importance_label: string;
  score_version: string;
  updated_at: string;
};

export type IssueImpactFactor = {
  name: string;
  label: string;
  weight: number;
  signal: number;
  contribution: number;
  raw_value: string | number | null;
  details: Record<string, unknown>;
};

export type IssueImpactAdmin = IssuePublicImpact & {
  signals: Record<string, unknown>;
  factors: IssueImpactFactor[];
  calculation_notes: string[];
};

export type DuplicateSuggestion = {
  issue: PublicIssueSummary;
  existing_issue_id: string;
  similarity_score: number;
  reason_breakdown: string[];
  distance_km: number;
  text_similarity: number;
  category_match: boolean;
  recommended_action: DuplicateRecommendedAction;
  image_similarity: number | null;
};

export type DuplicateSuggestionResponse = {
  status: DuplicateLookupStatus;
  matches: DuplicateSuggestion[];
};

export type RewriteResponse = {
  rewritten_title: string;
  rewritten_description: string;
  explanation: string;
  tone_classification: RewriteToneClassification | null;
};

export type IssueFeedbackResponse = {
  issue_id: string;
  action: SwipeAction;
  support_count: number;
  support_changed: boolean;
  public_impact_score: number | null;
  affected_people_estimate: number | null;
};

export type SupportExistingIssueInput = {
  candidate_title?: string | null;
  candidate_description?: string | null;
  candidate_category_id?: string | null;
  candidate_latitude?: number | null;
  candidate_longitude?: number | null;
  similarity_score?: number | null;
  distance_km?: number | null;
  text_similarity?: number | null;
  category_match?: boolean;
  reason_breakdown?: string[];
  image_hashes?: string[];
};

export type SupportExistingIssueResponse = {
  canonical_issue_id: string;
  duplicate_link_id: string | null;
  support_count: number;
  support_changed: boolean;
  public_impact_score: number;
  affected_people_estimate: number;
};

export type SupportTicketMessage = {
  id: string;
  ticket_id: string;
  author_id: string;
  body: string;
  is_internal: boolean;
  created_at: string;
  updated_at: string;
};

export type SupportTicket = {
  id: string;
  issue_id: string | null;
  author_id: string;
  type: "appeal" | "bug_report" | "improvement";
  status:
    | "open"
    | "under_review"
    | "waiting_for_user"
    | "resolved"
    | "closed";
  subject: string;
  messages: SupportTicketMessage[];
  created_at: string;
  updated_at: string;
};
