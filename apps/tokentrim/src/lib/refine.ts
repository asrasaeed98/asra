import Anthropic from "@anthropic-ai/sdk";
import type { RefineRequest, RefineResponse } from "./types";

const SYSTEM = `You are an expert prompt engineer focused on TOKEN EFFICIENCY. Your job is to rewrite user prompts so they use fewer tokens while preserving intent and improving clarity.

Primary goal: same meaning, fewer tokens. Every word must earn its place.

Rules:
- Remove filler, repetition, throat-clearing, and vague phrasing. Prefer precise verbs and nouns.
- Do not pad with unnecessary politeness, disclaimers, or meta-instructions to the model.
- Use structure (headers, bullets, XML) only when it reduces total tokens vs a tight paragraph.
- Put the critical instruction first. Constraints and output format at the end, stated once.
- Do not invent facts the user did not provide.
- Each variant must be copy-paste-ready — not commentary about the prompt.
- Variants must differ in compression strategy, not just synonym swaps.

Return ONLY valid JSON matching this schema:
{
  "variants": [
    {
      "id": "concise",
      "title": "Concise",
      "prompt": "string",
      "rationale": "one sentence on why this works",
      "practices": ["2-3 short bullets of techniques used"]
    },
    {
      "id": "structured",
      "title": "Structured",
      "prompt": "string",
      "rationale": "string",
      "practices": ["string"]
    },
    {
      "id": "contextual",
      "title": "Context-aware",
      "prompt": "string",
      "rationale": "string",
      "practices": ["string"]
    }
  ],
  "summary": "one sentence on token/efficiency tradeoffs across the three variants for this input"
}

Variant strategies (all must be leaner than the raw input when possible):
1. concise — aggressive compression; minimum tokens; no section headers unless they save tokens overall.
2. structured — efficient scaffolding (Role/Task/Output/Constraints or light XML); zero redundant lines.
3. contextual — weaves user goal/audience/format once, tightly; no repeated context blocks.`;

function buildUserMessage(body: RefineRequest): string {
  const parts = [`## Raw prompt\n${body.prompt.trim()}`];

  if (body.goal?.trim()) parts.push(`## Goal\n${body.goal.trim()}`);
  if (body.audience?.trim()) parts.push(`## Audience\n${body.audience.trim()}`);
  if (body.outputFormat?.trim()) parts.push(`## Desired output format\n${body.outputFormat.trim()}`);
  if (body.constraints?.trim()) parts.push(`## Constraints\n${body.constraints.trim()}`);
  if (body.extraContext?.trim()) parts.push(`## Extra context\n${body.extraContext.trim()}`);

  return parts.join("\n\n");
}

function parseResponse(text: string): RefineResponse {
  const trimmed = text.trim();
  const jsonStart = trimmed.indexOf("{");
  const jsonEnd = trimmed.lastIndexOf("}");
  if (jsonStart === -1 || jsonEnd === -1) {
    throw new Error("Model did not return JSON");
  }
  const parsed = JSON.parse(trimmed.slice(jsonStart, jsonEnd + 1)) as RefineResponse;
  if (!Array.isArray(parsed.variants) || parsed.variants.length !== 3) {
    throw new Error("Expected exactly 3 prompt variants");
  }
  return parsed;
}

export async function refinePrompt(body: RefineRequest): Promise<RefineResponse> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error("ANTHROPIC_API_KEY is not configured");
  }

  const model = process.env.ANTHROPIC_MODEL_TOKENTRIM ?? "claude-haiku-4-5";
  const client = new Anthropic({ apiKey });

  const message = await client.messages.create({
    model,
    max_tokens: 4096,
    temperature: 0.3,
    system: SYSTEM,
    messages: [{ role: "user", content: buildUserMessage(body) }],
  });

  const block = message.content.find((b) => b.type === "text");
  if (!block || block.type !== "text") {
    throw new Error("Empty model response");
  }

  return parseResponse(block.text);
}
