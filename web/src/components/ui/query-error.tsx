"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { ErrorRetry } from "./error-retry";

interface QueryErrorProps<TData, TError> {
  query: UseQueryResult<TData, TError>;
  label?: string;
}

/** Wrapper around TanStack Query error states.
 *  Renders ErrorRetry when query fails, with last-success tracking.
 */
export function QueryError<TData, TError>({
  query,
  label,
}: QueryErrorProps<TData, TError>) {
  if (!query.isError) return null;

  const error =
    query.error instanceof Error
      ? query.error
      : new Error(String(query.error) || "Unknown error");

  return (
    <ErrorRetry
      error={error}
      retry={() => query.refetch()}
      lastSuccessAt={query.dataUpdatedAt ? new Date(query.dataUpdatedAt) : null}
      label={label}
    />
  );
}
