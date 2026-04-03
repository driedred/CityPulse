"use client";

import { useAsyncResource } from "@/hooks/use-async-resource";
import { apiClient } from "@/lib/api/client";
import type {
  UserIntegrityDetail,
  UserIntegritySummary,
} from "@/lib/api/types";

export function useAdminIntegrityUsers(token: string | null, enabled: boolean) {
  return useAsyncResource<UserIntegritySummary[]>({
    initialValue: [],
    enabled: Boolean(token) && enabled,
    deps: [token ?? "", enabled],
    load: () => {
      if (!token || !enabled) {
        return Promise.resolve([]);
      }
      return apiClient.listAdminUsers(token);
    },
  });
}

export function useAdminUserIntegrityDetail(
  token: string | null,
  userId: string | null,
  enabled: boolean,
) {
  return useAsyncResource<UserIntegrityDetail | null>({
    initialValue: null,
    enabled: Boolean(token && userId) && enabled,
    deps: [token ?? "", userId ?? "", enabled],
    load: () => {
      if (!token || !userId || !enabled) {
        return Promise.resolve(null);
      }
      return apiClient.getAdminUserIntegrity(token, userId);
    },
  });
}
