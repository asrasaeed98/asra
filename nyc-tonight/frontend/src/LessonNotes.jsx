import { useEffect, useState } from "react";
import { LESSON1_PROMPTS } from "./lessons.js";

export function LessonNotes({ notes, onTryPrompt, loading }) {
  const [openIds, setOpenIds] = useState(() => new Set());

  // When a new lesson box appears, open only that one (collapse earlier ones).
  useEffect(() => {
    if (!notes?.sections?.length) return;
    const newestId = notes.sections[notes.sections.length - 1].id;
    setOpenIds(new Set([newestId]));
  }, [notes?.step]); // eslint-disable-line react-hooks/exhaustive-deps -- only on step advance

  if (!notes) return null;

  function toggle(id) {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const currentStep = notes.step;

  return (
    <aside className="notes" aria-label="Lesson notes">
      <div className="notes-inner">
        <p className="notes-kicker">Learning as you chat</p>
        <h2>{notes.title}</h2>

        <div className="lesson-accordion">
          {notes.sections.map((section) => {
            const open = openIds.has(section.id);
            return (
              <section
                key={section.id}
                className={
                  section.step === currentStep
                    ? "lesson-section current"
                    : "lesson-section"
                }
              >
                <button
                  type="button"
                  className="lesson-section-toggle"
                  aria-expanded={open}
                  onClick={() => toggle(section.id)}
                >
                  <span className="lesson-section-chevron" aria-hidden>
                    {open ? "▾" : "▸"}
                  </span>
                  <span className="lesson-section-title">{section.title}</span>
                  {section.step === currentStep && (
                    <span className="lesson-section-badge">now</span>
                  )}
                </button>
                {open && (
                  <div className="lesson-section-body">
                    {section.blocks.map((b) => (
                      <div key={b.heading} className="notes-block">
                        <h3>{b.heading}</h3>
                        <p>{b.body}</p>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            );
          })}
        </div>

        {currentStep === 0 && (
          <button
            type="button"
            className="notes-cta"
            disabled={loading}
            onClick={() => onTryPrompt(LESSON1_PROMPTS.first)}
          >
            Try: “{LESSON1_PROMPTS.first}”
          </button>
        )}

        {currentStep === 1 && (
          <button
            type="button"
            className="notes-cta secondary"
            disabled={loading}
            onClick={() => onTryPrompt(LESSON1_PROMPTS.second)}
          >
            Try: “{LESSON1_PROMPTS.second}”
          </button>
        )}
      </div>
    </aside>
  );
}
