/** Format AI summary text for display (no markdown titles). */

export type SummaryBlock =
  | { type: "header"; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] };

export function formatSummaryBlocks(
  text: string | null | undefined,
  blocks?: SummaryBlock[] | null,
): SummaryBlock[] {
  if (blocks && blocks.length > 0) {
    return blocks;
  }
  if (!text?.trim()) return [];
  return legacyTextToBlocks(text);
}

function legacyTextToBlocks(text: string): SummaryBlock[] {
  const lines = text.split("\n");
  const result: SummaryBlock[] = [];
  let paragraphLines: string[] = [];
  let listItems: string[] = [];

  const flushParagraph = () => {
    const joined = paragraphLines.join(" ").trim();
    if (joined) result.push({ type: "paragraph", text: joined });
    paragraphLines = [];
  };

  const flushList = () => {
    if (listItems.length) result.push({ type: "list", items: [...listItems] });
    listItems = [];
  };

  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      flushList();
      flushParagraph();
      continue;
    }
    if (/^#{1,6}\s/.test(t) || /^executive summary:/i.test(t)) continue;

    const bullet = t.match(/^[-*•]\s+(.+)/);
    if (bullet) {
      flushParagraph();
      listItems.push(bullet[1].trim());
      continue;
    }

    flushList();
    paragraphLines.push(t);
  }
  flushList();
  flushParagraph();

  if (result.length === 1 && result[0].type === "paragraph" && result[0].text.length > 320) {
    return splitLongParagraph(result[0].text);
  }
  return result;
}

function splitLongParagraph(text: string): SummaryBlock[] {
  const sentences = text.match(/[^.!?]+[.!?]+(\s|$)|[^.!?]+$/g)?.map((s) => s.trim()).filter(Boolean) ?? [text];
  if (sentences.length <= 2) return [{ type: "paragraph", text }];

  const intro = sentences.slice(0, 2).join(" ");
  const rest = sentences.slice(2);
  const blocks: SummaryBlock[] = [{ type: "paragraph", text: intro }];
  if (rest.length) blocks.push({ type: "list", items: rest });
  return blocks;
}

/** @deprecated use formatSummaryBlocks */
export function formatSummaryParagraphs(text: string): string[] {
  return formatSummaryBlocks(text)
    .flatMap((b) => (b.type === "paragraph" ? [b.text] : b.items))
    .filter(Boolean);
}
