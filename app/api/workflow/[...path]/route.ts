import { NextResponse } from "next/server";
import { normalizeContentOpsError } from "@/lib/contentops-contract";
import { createSupabaseServerClient } from "@/lib/supabase/server";

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL ?? "http://localhost:8000";
const CONTENTOPS_TIMEOUT_MS = 10_000;
const ALLOWED_ROOTS = new Set(["content-items", "writing-profile"]);

type RouteContext = { params: Promise<{ path: string[] }> };

async function forward(request: Request, context: RouteContext) {
  const requestId = crypto.randomUUID();
  const { path } = await context.params;
  if (!path.length || !ALLOWED_ROOTS.has(path[0])) {
    return NextResponse.json(
      { error: "Unknown workflow route.", code: "unknown_workflow_route", requestId },
      { status: 404 }
    );
  }

  const encodedPath = path.map((segment) => encodeURIComponent(segment)).join("/");
  const query = new URL(request.url).search;

  try {
    const supabase = await createSupabaseServerClient();
    const session = supabase ? (await supabase.auth.getSession()).data.session : null;
    if (supabase && !session?.access_token) {
      return NextResponse.json(
        { error: "Your session has expired. Sign in again.", code: "authentication_required", requestId },
        { status: 401, headers: { "X-Request-ID": requestId } }
      );
    }
    const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
    const backendResponse = await fetch(`${PYTHON_BACKEND_URL}/${encodedPath}${query}`, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
        ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {})
      },
      body: body || undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(CONTENTOPS_TIMEOUT_MS)
    });
    const data: unknown = await backendResponse.json().catch(() => null);
    if (!backendResponse.ok) {
      const error = normalizeContentOpsError(data, requestId);
      return NextResponse.json(error, {
        status: backendResponse.status,
        headers: { "X-Request-ID": error.requestId }
      });
    }
    return NextResponse.json(data, {
      status: backendResponse.status,
      headers: { "X-Request-ID": backendResponse.headers.get("X-Request-ID") ?? requestId }
    });
  } catch (error) {
    const timedOut = error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError");
    console.error("Workflow backend request failed", { requestId, timedOut, error });
    return NextResponse.json(
      {
        error: timedOut
          ? "The content workflow did not respond in time."
          : "The content workflow is unavailable. Start the Python backend on port 8000 and try again.",
        code: timedOut ? "backend_timeout" : "backend_unavailable",
        requestId
      },
      { status: timedOut ? 504 : 503, headers: { "X-Request-ID": requestId } }
    );
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
