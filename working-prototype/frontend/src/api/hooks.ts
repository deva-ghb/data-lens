import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from "@tanstack/react-query";
import type { AiDraft } from "../ui/AiSection";
import { useToast } from "../ui/Toast";
import { apiGet, apiSend, type ApiError } from "./client";

/** Read from the API. The key is the path, so any write that touches it can refresh it. */
export function useGet<T>(path: string | null, options: Partial<UseQueryOptions<T, ApiError>> = {}) {
  return useQuery<T, ApiError>({
    queryKey: [path],
    queryFn: () => apiGet<T>(path as string),
    enabled: path !== null,
    staleTime: 15_000,
    ...options,
  });
}

type SendOptions<Result> = { onSuccess?: (result: Result) => void; onError?: (error: ApiError) => void };

/** Write to the API, then refresh every cached read (the screens stay in step).
 *  A refusal is never silent: unless the screen handles it, the server's own sentence is
 *  shown, and the screen refreshes so a stale view corrects itself. */
export function useSend<Body = unknown, Result = unknown>(
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  path: string | ((body: Body) => string),
) {
  const client = useQueryClient();
  const toast = useToast();
  const mutation = useMutation<Result, ApiError, Body>({
    mutationFn: (body: Body) =>
      apiSend<Result>(method, typeof path === "function" ? path(body) : path, body),
    onSuccess: () => client.invalidateQueries(),
    onError: () => client.invalidateQueries(),
  });
  const mutate = (body: Body, options: SendOptions<Result> = {}) =>
    mutation.mutate(body, {
      onSuccess: options.onSuccess,
      onError: options.onError ?? ((e) => toast({ title: "That did not go through", body: e.message, tone: "critical" })),
    });
  return { ...mutation, mutate };
}

export type ApiDraft = Omit<AiDraft, "confirmed_by"> & { confirmed_by?: string | null };

export function toDraft(d: ApiDraft | null | undefined): AiDraft | null {
  if (!d) return null;
  return { ...d, confirmed_by: d.confirmed_by ?? undefined };
}
