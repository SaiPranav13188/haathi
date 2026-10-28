// Server-side backend status check. Always answers 200 so a sleeping free-tier backend never shows up as a
// browser console error; the body says whether the backend is awake.
const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const r = await fetch(`${BACKEND}/api/health`, { cache: "no-store", signal: AbortSignal.timeout(9000) });
    return Response.json({ ok: r.ok });
  } catch {
    return Response.json({ ok: false });
  }
}
