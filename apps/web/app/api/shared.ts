import { NextRequest, NextResponse } from "next/server";
export const apiBase = process.env.API_BASE_URL || "http://127.0.0.1:8000";
export const cookieName = "fincathon_session";
export async function boundedBody(
  request: NextRequest,
  limit = 16 * 1024 * 1024,
) {
  const declared = request.headers.get("content-length");
  if (declared && (!/^\d+$/.test(declared) || Number(declared) > limit))
    throw new RangeError("Request body exceeds the limit.");
  const reader = request.body?.getReader();
  if (!reader) return new Uint8Array();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      size += next.value.byteLength;
      if (size > limit) {
        await reader.cancel();
        throw new RangeError("Request body exceeds the limit.");
      }
      chunks.push(next.value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes;
}
export function originError(request: NextRequest) {
  if (["GET", "HEAD"].includes(request.method)) return null;
  const origin = request.headers.get("origin");
  const allowed = process.env.WEB_ORIGIN
    ? [process.env.WEB_ORIGIN]
    : ["http://localhost:3000", "http://127.0.0.1:3000"];
  if (
    !origin ||
    !allowed.includes(origin) ||
    request.headers.get("sec-fetch-site") === "cross-site"
  )
    return NextResponse.json(
      { message: "Cross-origin requests are not allowed." },
      { status: 403 },
    );
  return null;
}
