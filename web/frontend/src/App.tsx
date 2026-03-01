import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "@/components/layout/Layout";
import { InputForm } from "@/components/input/InputForm";
import { ResultsPanel } from "@/components/results/ResultsPanel";
import { ProjectExplorer } from "@/components/sidebar/ProjectExplorer";

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
      <Layout sidebar={<ProjectExplorer />}>
        {/* Two-column layout: input left, results right.
            On small screens both columns stack vertically. */}
        <div className="flex flex-col lg:flex-row gap-6 p-6">
          {/* Input form – slightly narrower column */}
          <div className="w-full lg:w-1/2 xl:w-2/5 shrink-0">
            <InputForm />
          </div>

          {/* Results panel – wider column */}
          <div className="w-full lg:w-1/2 xl:w-3/5 min-w-0">
            <ResultsPanel />
          </div>
        </div>
      </Layout>
    </QueryClientProvider>
  );
}

export default App;
