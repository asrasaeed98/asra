/** Curriculum for Agent Lab. v1 ships Lesson 1 only. */

export const LESSONS = [
  {
    id: "lesson-1",
    number: 1,
    title: "Basics of agents",
    available: true,
  },
  {
    id: "lesson-2",
    number: 2,
    title: "Tool schemas & prompts",
    available: false,
  },
  {
    id: "lesson-3",
    number: 3,
    title: "Failure modes",
    available: false,
  },
];

export const LESSON1_PROMPTS = {
  first: "Find me dinner in Chinatown tonight",
  second: "What's the weather like today?",
};

const STEP_META = [
  { id: "start", title: "Chatbot vs agent" },
  { id: "first-tools", title: "What just happened" },
  { id: "another-tool", title: "Another tool" },
  { id: "recap", title: "Lesson 1 recap" },
];

/**
 * Derive Lesson 1 journey step from interaction state.
 * 0 start → 1 first tools seen → 2 multi-tool / second turn → 3 recap
 */
export function lesson1Step({ userTurns, latestTrace }) {
  if (userTurns < 1) return 0;
  const tools = latestTrace?.tools_used || [];
  const multi = tools.length >= 2;
  if (userTurns >= 2 || multi) return userTurns >= 2 ? 3 : 2;
  if (tools.length >= 1) return 1;
  return 1;
}

/** All sections unlocked up to `step`, for expandable lesson memory. */
export function buildLesson1Sections({ step, latestTrace }) {
  const tools = latestTrace?.tools_used || [];
  const max = Math.max(0, Math.min(step, STEP_META.length - 1));
  const sections = [];
  for (let s = 0; s <= max; s++) {
    sections.push({
      id: STEP_META[s].id,
      step: s,
      title: STEP_META[s].title,
      blocks: notesBlocks(s, tools),
      defaultOpen: s === max,
    });
  }
  return {
    title: "Lesson 1: Basics of agents",
    step: max,
    provider: latestTrace?.provider,
    model: latestTrace?.model,
    sections,
  };
}

function notesBlocks(step, tools) {
  // Each step adds one new idea; avoid re-explaining frontend/backend/LLM.
  if (step === 0) {
    return [
      {
        heading: "The difference",
        body: "A chatbot only writes text. An agent can also call tools (APIs or code), read the results, then answer.",
      },
      {
        heading: "This demo",
        body: "NYC Tonight can search restaurants, check weather, find events, and build reservation links. Try the prompt below (or type your own).",
      },
    ];
  }

  if (step === 1) {
    const toolList = tools.length
      ? `This turn called: ${tools.map((t) => `\`${t}\``).join(", ")}.`
      : "No tool ran this turn. Try asking for restaurants or weather.";
    return [
      {
        heading: "The three parts",
        body: `Frontend sends your message. Backend runs tools. The LLM is the brain that decides which tool to use and what to say. ${toolList}`,
      },
      {
        heading: "Try next",
        body: "Ask only about the weather. You should see a different tool: get_weather.",
      },
    ];
  }

  if (step === 2) {
    const used = tools.length
      ? `This time: ${tools.map((t) => `\`${t}\``).join(", ")}.`
      : "Ask about the weather if you have not yet.";
    return [
      {
        heading: "Same loop, new tool",
        body: `${used} The LLM picks tools from the current ask, not from earlier chat topics.`,
      },
      {
        heading: "Grounding",
        body: "Cards in chat come from tool results. If a tool did not return it, the agent should not invent it.",
      },
    ];
  }

  return [
    {
      heading: "Takeaways",
      body: "An agent needs policy (system prompt), tools (capabilities), and a loop (decide → act → observe → answer). The LLM decides; the backend acts.",
    },
    {
      heading: "Coming soon",
      body: "Lesson 2 covers tool schemas and prompts. Lesson 3 covers failure modes. Open the menu anytime.",
    },
  ];
}
