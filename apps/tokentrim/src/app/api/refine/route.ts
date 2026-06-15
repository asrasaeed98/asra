import { NextResponse } from "next/server";
import { refinePrompt } from "@/lib/refine";
import type { RefineRequest } from "@/lib/types";

export async function POST(request: Request) {
  let body: RefineRequest;
  try {
    body = (await request.json()) as RefineRequest;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const prompt = body.prompt?.trim();
  if (!prompt) {
    return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  }
  if (prompt.length > 8000) {
    return NextResponse.json({ error: "prompt must be at most 8000 characters" }, { status: 400 });
  }

  try {
    const result = await refinePrompt(body);
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Refinement failed";
    const status = message.includes("ANTHROPIC_API_KEY") ? 503 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
