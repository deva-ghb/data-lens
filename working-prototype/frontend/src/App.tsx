import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { apiGet } from "./api/client";

type Health = { status: string };

// The component gallery exists only in development builds; production drops it entirely.
const Kit = import.meta.env.DEV ? lazy(() => import("./pages/Kit")) : null;

function Home() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<Health>("/api/health"),
  });

  return (
    <main>
      <h1>Data Lens</h1>
      {health.isPending && <p>Checking the service</p>}
      {health.isError && <p role="alert">Service not reachable: {health.error.message}</p>}
      {health.isSuccess && (
        <p>
          Service status: <span data-testid="health-status">{health.data.status}</span>
        </p>
      )}
    </main>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      {Kit !== null && (
        <Route
          path="/kit"
          element={
            <Suspense fallback={null}>
              <Kit />
            </Suspense>
          }
        />
      )}
    </Routes>
  );
}
