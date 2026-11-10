import { createFileRoute } from "@tanstack/react-router";
import { EmptyDataState } from "@/components/ff/primitives";

export const Route = createFileRoute("/_workspace/analysts")({
  head: () => ({
    meta: [
      { title: "Analyst Research — Foundation Flow" },
      { name: "description", content: "Analyst Research in Foundation Flow, the fundamental stock research platform." },
      { property: "og:title", content: "Analyst Research — Foundation Flow" },
      { property: "og:description", content: "Analyst Research in Foundation Flow, the fundamental stock research platform." },
    ],
  }),
  component: () => (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <div className="eyebrow mb-2">Research</div>
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Analyst Research</h1>
      </div>
      <EmptyDataState title="Arriving in the next phase" body="This module will be powered by your PostgreSQL landing schema once the connection is configured." />
    </div>
  ),
});
