import { siteConfig } from "@/lib/site";
import type {
  ApiErrorPayload,
  AuthTokenResponse,
  DuplicateSuggestionResponse,
  Issue,
  IssueAttachment,
  IssueCategory,
  IssueFeedbackResponse,
  IssueImpactAdmin,
  IssuePublicImpact,
  PublicIssueDetail,
  PublicIssueMapMarker,
  PublicIssueSort,
  PublicIssueSummary,
  RewriteResponse,
  SupportExistingIssueInput,
  SupportExistingIssueResponse,
  SupportTicket,
  SwipeAction,
  User,
} from "@/lib/api/types";

type RequestOptions = RequestInit & {
  token?: string | null;
};

export class ApiError extends Error {
  status: number;
  code: string | undefined;
  details: unknown;

  constructor(
    message: string,
    {
      status,
      code,
      details,
    }: {
      status: number;
      code?: string;
      details?: unknown;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function buildUrl(path: string, searchParams?: URLSearchParams) {
  const url = new URL(path, siteConfig.apiBaseUrl);
  if (searchParams) {
    url.search = searchParams.toString();
  }
  return url.toString();
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
  searchParams?: URLSearchParams,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(buildUrl(path, searchParams), {
    ...options,
    headers,
    cache: options.cache ?? "no-store",
  });

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null;

    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = null;
    }

    throw new ApiError(payload?.error.message ?? "Request failed.", {
      status: response.status,
      code: payload?.error.code,
      details: payload?.error.details,
    });
  }

  return (await response.json()) as T;
}

export const apiClient = {
  async register(input: {
    email: string;
    password: string;
    full_name: string;
    preferred_locale: string;
  }) {
    return request<User>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async login(input: { email: string; password: string }) {
    return request<AuthTokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async getCurrentUser(token: string) {
    return request<User>("/api/users/me", { token });
  },

  async listCategories() {
    return request<IssueCategory[]>("/api/public/categories");
  },

  async listPublicIssues(input: {
    sort?: PublicIssueSort;
    categoryId?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    limit?: number;
  }) {
    const params = new URLSearchParams();
    if (input.sort) params.set("sort", input.sort);
    if (input.categoryId) params.set("category_id", input.categoryId);
    if (typeof input.latitude === "number") params.set("latitude", String(input.latitude));
    if (typeof input.longitude === "number") params.set("longitude", String(input.longitude));
    if (input.limit) params.set("limit", String(input.limit));

    return request<PublicIssueSummary[]>("/api/public/issues", {}, params);
  },

  async listSwipeFeed(input: {
    sort?: PublicIssueSort;
    categoryId?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    limit?: number;
    excludeIssueIds?: string[];
  }) {
    const params = new URLSearchParams();
    if (input.sort) params.set("sort", input.sort);
    if (input.categoryId) params.set("category_id", input.categoryId);
    if (typeof input.latitude === "number") params.set("latitude", String(input.latitude));
    if (typeof input.longitude === "number") params.set("longitude", String(input.longitude));
    if (input.limit) params.set("limit", String(input.limit));
    input.excludeIssueIds?.forEach((issueId) => params.append("exclude_issue_ids", issueId));

    return request<PublicIssueSummary[]>("/api/public/issues/feed", {}, params);
  },

  async listMapIssues(input: {
    categoryId?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    limit?: number;
  }) {
    const params = new URLSearchParams();
    if (input.categoryId) params.set("category_id", input.categoryId);
    if (typeof input.latitude === "number") params.set("latitude", String(input.latitude));
    if (typeof input.longitude === "number") params.set("longitude", String(input.longitude));
    if (input.limit) params.set("limit", String(input.limit));

    return request<PublicIssueMapMarker[]>("/api/public/issues/map", {}, params);
  },

  async getPublicIssue(issueId: string) {
    return request<PublicIssueDetail>(`/api/public/issues/${issueId}`);
  },

  async getPublicIssueImpact(issueId: string) {
    return request<IssuePublicImpact>(`/api/public/issues/${issueId}/impact`);
  },

  async getIssueAdminImpact(token: string, issueId: string) {
    return request<IssueImpactAdmin>(`/api/issues/${issueId}/impact/admin`, {
      token,
    });
  },

  async submitIssue(
    token: string,
    input: {
      title: string;
      short_description: string;
      category_id: string;
      latitude: number;
      longitude: number;
      source_locale: string;
    },
  ) {
    return request<Issue>("/api/issues", {
      method: "POST",
      token,
      body: JSON.stringify(input),
    });
  },

  async createAttachmentMetadata(
    token: string,
    issueId: string,
    input: {
      original_filename: string;
      content_type: string;
      size_bytes: number;
      storage_key: string;
    },
  ) {
    return request<IssueAttachment>(`/api/issues/${issueId}/attachments`, {
      method: "POST",
      token,
      body: JSON.stringify(input),
    });
  },

  async listOwnIssues(token: string) {
    return request<Issue[]>("/api/issues/me", { token });
  },

  async listOwnTickets(token: string) {
    return request<SupportTicket[]>("/api/tickets/me", { token });
  },

  async createTicket(
    token: string,
    input: {
      issue_id: string | null;
      type: "appeal" | "bug_report" | "improvement";
      subject: string;
      message: string;
    },
  ) {
    return request<SupportTicket>("/api/tickets", {
      method: "POST",
      token,
      body: JSON.stringify(input),
    });
  },

  async suggestDuplicates(input: {
    title: string;
    short_description: string;
    latitude: number;
    longitude: number;
    category_id?: string | null;
  }) {
    return request<DuplicateSuggestionResponse>("/api/public/issues/duplicates", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async rewriteIssueText(input: {
    title: string;
    short_description: string;
  }) {
    return request<RewriteResponse>("/api/public/issues/rewrite", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async sendIssueFeedback(
    token: string,
    issueId: string,
    action: SwipeAction,
  ) {
    return request<IssueFeedbackResponse>(`/api/public/issues/${issueId}/feedback`, {
      method: "POST",
      token,
      body: JSON.stringify({ action }),
    });
  },

  async supportExistingIssue(
    token: string,
    issueId: string,
    input: SupportExistingIssueInput,
  ) {
    return request<SupportExistingIssueResponse>(`/api/public/issues/${issueId}/support`, {
      method: "POST",
      token,
      body: JSON.stringify(input),
    });
  },
};
