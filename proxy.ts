import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { getSupabasePublicConfig } from "@/lib/supabase/config";
import { safeReturnPath } from "@/lib/auth-return";

export async function proxy(request: NextRequest) {
  const config = getSupabasePublicConfig();
  if (!config) return NextResponse.next({ request });

  let response = NextResponse.next({ request });
  const supabase = createServerClient(config.url, config.publishableKey, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (cookiesToSet) => {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      }
    }
  });

  const { data } = await supabase.auth.getClaims();
  const pathname = request.nextUrl.pathname;
  const isAuthRoute = pathname.startsWith("/login") || pathname.startsWith("/auth/");
  const isApiRoute = pathname.startsWith("/api/");
  function redirectWithSession(url: URL) {
    const target = NextResponse.redirect(url);
    response.cookies.getAll().forEach((cookie) => target.cookies.set(cookie));
    return target;
  }

  if (!data?.claims && !isAuthRoute && !isApiRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    url.searchParams.set("next", safeReturnPath(request.nextUrl.pathname + request.nextUrl.search));
    return redirectWithSession(url);
  }
  if (data?.claims && pathname === "/login") {
    const url = request.nextUrl.clone();
    return redirectWithSession(new URL(safeReturnPath(request.nextUrl.searchParams.get("next")), url));
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"]
};
