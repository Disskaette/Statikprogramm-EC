import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "@/components/layout/Layout";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Layout
        sidebar={
          <div className="p-4">
            <h2 className="text-sm font-semibold text-[var(--muted-foreground)] mb-3">
              Projekt-Explorer
            </h2>
            <p className="text-xs text-[var(--muted-foreground)] italic">
              Wird in Phase 5 implementiert
            </p>
          </div>
        }
      >
        <div className="flex h-full items-center justify-center">
          <div className="text-center space-y-4">
            <h1 className="text-3xl font-bold">Statik-Tool v2.0</h1>
            <p className="text-[var(--muted-foreground)]">
              Durchlauftr&auml;ger-Berechnung nach EC5
            </p>
            <p className="text-sm text-[var(--muted-foreground)]">
              Willkommen! Die Eingabemaske wird in Phase 2 implementiert.
            </p>
          </div>
        </div>
      </Layout>
    </QueryClientProvider>
  );
}

export default App;
