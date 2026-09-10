import { proxyToBackend } from "@/lib/proxy";

// /api/<path> → BACKEND_URL/<path>; see lib/proxy.ts for why.
async function handle(request: Request, ctx: RouteContext<"/api/[...path]">) {
  const { path } = await ctx.params;
  return proxyToBackend(request, path.join("/"));
}

export const GET = handle;
export const POST = handle;
