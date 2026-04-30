"use client";

import { useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

export default function Providers({
  children,
}: {
  children: React.ReactNode;
}) {
  // ✅ Create client per app instance (correct pattern)
  const [queryClient] = useState(() =>
    new QueryClient({
      defaultOptions: {
        queries: {
          retry: 1, // avoid infinite retries
          refetchOnWindowFocus: false,
        },
        mutations: {
          retry: 1,
        },
      },
    })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}

      {/* ✅ Devtools (only in development) */}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}