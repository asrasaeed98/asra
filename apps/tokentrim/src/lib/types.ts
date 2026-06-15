export type RefineRequest = {
  prompt: string;
  goal?: string;
  audience?: string;
  outputFormat?: string;
  constraints?: string;
  extraContext?: string;
};

export type PromptVariant = {
  id: "concise" | "structured" | "contextual";
  title: string;
  prompt: string;
  rationale: string;
  practices: string[];
};

export type RefineResponse = {
  variants: PromptVariant[];
  summary: string;
};

export const VARIANT_LABELS: Record<PromptVariant["id"], string> = {
  concise: "Concise",
  structured: "Structured",
  contextual: "Context-aware",
};
