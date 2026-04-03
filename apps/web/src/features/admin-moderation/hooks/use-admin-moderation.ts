"use client";

import { apiClient } from "@/lib/api/client";
import type {
  AdminModerationIssue,
  IssueModerationAudit,
} from "@/lib/api/types";
import { useAsyncResource } from "@/hooks/use-async-resource";

export function useAdminModerationIssues(token: string | null, enabled: boolean) {
  return useAsyncResource<AdminModerationIssue[]>({
    initialValue: [],
    enabled: Boolean(token) && enabled,
    deps: [token ?? "", enabled],
    load: () => {
      if (!token || !enabled) {
        return Promise.resolve([]);
      }
      return apiClient.listAdminModerationIssues(token);
    },
  });
}

export function useAdminModerationIssueDetail(
  token: string | null,
  issueId: string | null,
  enabled: boolean,
) {
  return useAsyncResource<IssueModerationAudit | null>({
    initialValue: null,
    enabled: Boolean(token && issueId) && enabled,
    deps: [token ?? "", issueId ?? "", enabled],
    load: () => {
      if (!token || !issueId || !enabled) {
        return Promise.resolve(null);
      }
      return apiClient.getAdminModerationIssue(token, issueId);
    },
  });
}
