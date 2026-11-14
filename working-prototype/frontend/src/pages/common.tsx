import type { ReactNode } from "react";
import { ErrorState } from "../ui/ErrorState";
import { Skeleton } from "../ui/Skeleton";
import type { ApiError } from "../api/client";

/** Loading, error or content: the three states every screen has. */
export function Loaded<T>({
  query,
  children,
  lines = 6,
}: {
  query: { isPending: boolean; isError: boolean; error: ApiError | null; data: T | undefined; refetch: () => unknown };
  children: (data: T) => ReactNode;
  lines?: number;
}) {
  if (query.isPending) return <Skeleton lines={lines} />;
  if (query.isError || query.data === undefined) {
    return (
      <ErrorState
        title={query.error?.status === 403 ? "Not available for your role" : "This could not be loaded"}
        message={query.error?.message ?? "Please try again."}
        onRetry={query.error?.status === 403 ? undefined : () => query.refetch()}
      />
    );
  }
  return <>{children(query.data)}</>;
}

export function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function titleCase(text: string): string {
  const spaced = text.split("_").join(" ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
