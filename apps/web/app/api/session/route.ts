import { NextRequest, NextResponse } from "next/server";
import { apiBase, boundedBody, cookieName, originError } from "../shared";
export async function POST(request: NextRequest) {
  const blocked = originError(request);
  if (blocked) return blocked;
  let body;
  try {
    body = JSON.parse(
      new TextDecoder().decode(await boundedBody(request, 64 * 1024)),
    );
  } catch (error) {
    return NextResponse.json(
      { message: "Isi sesi tidak valid atau terlalu besar." },
      { status: error instanceof RangeError ? 413 : 400 },
    );
  }
  const demo = body.user_id !== undefined;
  const response = await fetch(
    apiBase + (demo ? "/v2/auth/demo-session" : "/v2/auth/login"),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    },
  );
  const data = await response.json();
  if (!response.ok) return NextResponse.json(data, { status: response.status });
  const result = NextResponse.json({ session: data.result.session });
  result.cookies.set(cookieName, data.result.access_token, {
    httpOnly: true,
    secure: request.nextUrl.protocol === "https:",
    sameSite: "strict",
    path: "/",
    maxAge: 8 * 3600,
  });
  return result;
}
export async function DELETE(request: NextRequest) {
  const blocked = originError(request);
  if (blocked) return blocked;
  const token = request.cookies.get(cookieName)?.value;
  if (token)
    await fetch(apiBase + "/v2/auth/logout", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + token,
        "Idempotency-Key": crypto.randomUUID(),
      },
    });
  const response = NextResponse.json({ message: "Keluar" });
  response.cookies.delete(cookieName);
  return response;
}
