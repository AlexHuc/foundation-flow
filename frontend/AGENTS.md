<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.

## What Lovable manages

Rules outside this block are the project's own. Change the pieces below in
Lovable, not by hand. With the [Lovable MCP](https://mcp.lovable.dev)
connected, `send_message` asks Lovable to do it; otherwise ask the user to
use the editor.

- **Database.** Do not add or edit `supabase/migrations/` or `drizzle/`.
  Ask Lovable to change the schema.
- **Generated files.** Do not edit a file whose header says it is automatically
  generated.
- **AI gateway.** Keep model calls on Lovable's gateway, and keep
  `LOVABLE_API_KEY` out of browser code.
- **Connectors.** Lovable provides native connectors. `list_connectors` shows
  which are enabled; `add_connector` only returns the dashboard link. When a
  connector is enabled, calls go through the connector gateway and need
  `LOVABLE_API_KEY`. When Lovable does not provide one, users can bring their
  own key and store it in Secrets.
- **Secrets.** Lovable manages them. Do not put secret values in the repo.
<!-- LOVABLE:END -->

## Project rules
- Financial market data comes from the user's existing PostgreSQL `landing` schema (read-only, server-side only); `src/lib/sample-data.ts` is an illustrative stand-in until that connection exists, and every surface using it must show the "Illustrative" label.
- The frontend reads market data through `src/lib/api.ts`, which calls the FastAPI backend at `VITE_API_BASE_URL` and falls back to the illustrative sample data when it is unset or unreachable; data labels must reflect the returned `source`.
- Derived metrics go through `src/lib/metrics.ts`, which returns null instead of fabricating values when inputs are missing.
- Workspace pages live under the `_workspace` pathless layout (sidebar + top nav); the landing page `/` sits outside it.
