import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from "@tanstack/react-query";
import { useRef } from "react";
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
  // Callbacks live with the mutation, not the component: a card that disappears once the
  // data refreshes must still show its confirmation.
  const callbacks = useRef<SendOptions<Result>>({});
  const mutation = useMutation<Result, ApiError, Body>({
    mutationFn: (body: Body) =>
      apiSend<Result>(method, typeof path === "function" ? path(body) : path, body),
    onSuccess: (result) => {
      callbacks.current.onSuccess?.(result);
      return client.invalidateQueries();
    },
    onError: (e) => {
      const handle = callbacks.current.onError ?? ((err: ApiError) => toast({ title: "That did not go through", body: err.message, tone: "critical" }));
      handle(e);
      return client.invalidateQueries();
    },
  });
  const mutate = (body: Body, options: SendOptions<Result> = {}) => {
    callbacks.current = options;
    mutation.mutate(body);
  };
  return { ...mutation, mutate };
}

export type ApiDraft = Omit<AiDraft, "confirmed_by"> & { confirmed_by?: string | null };

export function toDraft(d: ApiDraft | null | undefined): AiDraft | null {
  if (!d) return null;
  return { ...d, confirmed_by: d.confirmed_by ?? undefined };
}
