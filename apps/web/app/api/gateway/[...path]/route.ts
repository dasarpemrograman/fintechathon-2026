import { NextRequest, NextResponse } from "next/server";
import { apiBase, boundedBody, cookieName, originError } from "../../shared";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const blocked = originError(request);
  if (blocked) return blocked;
  const { path } = await context.params;
  // Authentication is handled only by the cookie-setting route. Never proxy bearer tokens to a client.
  if (
    path[0] === "auth" &&
    path.join("/") !== "auth/session" &&
    path.join("/") !== "auth/demo-identities" &&
    path.join("/") !== "auth/organization"
  )
    return NextResponse.json(
      { message: "This route is unavailable." },
      { status: 404 },
    );
  if (path.some((p) => !/^[-a-zA-Z0-9_]+$/.test(p)))
    return NextResponse.json({ message: "Invalid route." }, { status: 400 });
  const headers = new Headers();
  const token = request.cookies.get(cookieName)?.value;
  if (token) headers.set("Authorization", "Bearer " + token);
  const type = request.headers.get("content-type");
  if (type) headers.set("Content-Type", type);
  if (request.method !== "GET")
    headers.set(
      "Idempotency-Key",
      request.headers.get("Idempotency-Key") || crypto.randomUUID(),
    );
  let body: Uint8Array | undefined;
  try {
    body = request.method === "GET" ? undefined : await boundedBody(request);
  } catch (error) {
    if (!(error instanceof RangeError)) throw error;
    return NextResponse.json(
      { message: "The request exceeds the 16 MiB limit." },
      { status: 413 },
    );
  }
  const response = await fetch(
    apiBase +
      "/v2/" +
      path.map(encodeURIComponent).join("/") +
      request.nextUrl.search,
    {
      method: request.method,
      headers,
      body: body as BodyInit | undefined,
      cache: "no-store",
      redirect: "error",
    },
  );
  const out = new Headers({ "Cache-Control": "no-store" });
  for (const name of ["Content-Type", "Content-Disposition", "X-Request-ID"]) {
    const value = response.headers.get(name);
    if (value) out.set(name, value);
  }
  return new Response(response.body, { status: response.status, headers: out });
}
export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
