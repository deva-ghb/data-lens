import { ChevronDown, ChevronRight, CircleCheck, FilePenLine, TriangleAlert } from "lucide-react";
import { useId, useState } from "react";
import { Button } from "./Button";
import { BulletList, ReasoningPanel, type Reasoning } from "./ReasoningPanel";
import { TextArea } from "./TextArea";
import "./ui.css";

export type AiDraft = {
  id: string;
  kind: string;
  content: string;
  sure: string[];
  unsure: string[];
  would_change: string[];
  confidence: number;
  reasoning: Reasoning;
  status: "draft" | "confirmed" | "unavailable";
  confirmed_by?: string;
  model?: string;
};

export type AiSectionProps = {
  draft: AiDraft;
  onConfirm: (content: string) => void;
  onEdit: (content: string) => void;
  confirmLabel: string;
  title?: string;
  busy?: boolean;
};

function confidenceWord(confidence: number): string {
  if (confidence >= 0.75) return "High";
  if (confidence >= 0.5) return "Medium";
  return "Low";
}

/**
 * The text box starts from the draft, so a different draft (a new record, or a
 * retry that now has text) must start a fresh editor rather than keep old text.
 */
export function AiSection(props: AiSectionProps) {
  return <AiSectionBody key={`${props.draft.id}:${props.draft.status}`} {...props} />;
}

function AiSectionBody({
  draft,
  onConfirm,
  onEdit,
  confirmLabel,
  title = "Suggested draft",
  busy = false,
}: AiSectionProps) {
  const [text, setText] = useState(draft.content);
  const [showReasoning, setShowReasoning] = useState(false);
  const textId = useId();
  const reasoningId = useId();

  const change = (next: string) => {
    setText(next);
    onEdit(next);
  };

  if (draft.status === "confirmed") {
    return (
      <section className="dl-ai" aria-label={title}>
        <div className="dl-ai__header">
          <h3 className="dl-ai__title">
            <FilePenLine size={16} aria-hidden="true" />
            {title}
          </h3>
          <span className="dl-chip dl-chip--good">
            <CircleCheck aria-hidden="true" />
            {draft.confirmed_by !== undefined ? `Confirmed by ${draft.confirmed_by}` : "Confirmed"}
          </span>
        </div>
        <p className="dl-ai__confirmed">{draft.content}</p>
      </section>
    );
  }

  const unavailable = draft.status === "unavailable";
  const percent = Math.round(draft.confidence * 100);

  return (
    <section className="dl-ai" aria-label={title}>
      <div className="dl-ai__header">
        <h3 className="dl-ai__title">
          <FilePenLine size={16} aria-hidden="true" />
          {title}
        </h3>
        {!unavailable && (
          <div className="dl-ai__meta">
            <span className="dl-chip dl-chip--periwinkle">Draft, not yet confirmed</span>
            <span className="num">
              {confidenceWord(draft.confidence)} confidence ({percent}%)
            </span>
          </div>
        )}
      </div>

      {unavailable && (
        <div className="dl-ai__notice" role="status">
          <TriangleAlert aria-hidden="true" />
          <div>
            <p className="dl-ai__notice-title">Draft not available</p>
            <p className="dl-ai__notice-body">
              No draft could be written this time. Write it yourself below; nothing has been filled
              in for you.
            </p>
          </div>
        </div>
      )}

      <div className="dl-field">
        <label className="dl-field__label" htmlFor={textId}>
          {unavailable ? "Your text" : "Text to confirm"}
        </label>
        <TextArea
          id={textId}
          value={text}
          rows={unavailable ? 5 : 6}
          onChange={(event) => change(event.target.value)}
        />
      </div>

      {!unavailable && (
        <div className="dl-ai__lists">
          <section className="dl-reasoning__group" aria-label="Sure about">
            <h4 className="dl-reasoning__heading">Sure about</h4>
            <BulletList items={draft.sure} />
          </section>
          <section className="dl-reasoning__group" aria-label="Not sure about">
            <h4 className="dl-reasoning__heading">Not sure about</h4>
            <BulletList items={draft.unsure} />
          </section>
          <section className="dl-reasoning__group" aria-label="Would change the advice">
            <h4 className="dl-reasoning__heading">Would change the advice</h4>
            <BulletList items={draft.would_change} />
          </section>
        </div>
      )}

      {!unavailable && (
        <div className="dl-ai__reasoning">
          <Button
            variant="ghost"
            size="sm"
            className="dl-ai__reasoning-toggle"
            icon={showReasoning ? <ChevronDown /> : <ChevronRight />}
            aria-expanded={showReasoning}
            aria-controls={reasoningId}
            onClick={() => setShowReasoning((open) => !open)}
          >
            How this draft was worked out
          </Button>
          {showReasoning && (
            <div id={reasoningId} className="dl-ai__reasoning-body">
              <ReasoningPanel reasoning={draft.reasoning} />
            </div>
          )}
        </div>
      )}

      <div className="dl-ai__footer">
        <p className="dl-ai__footnote">
          {unavailable
            ? "Saved under your name once you confirm."
            : "Nothing is saved until a person confirms it."}
        </p>
        <Button
          variant="primary"
          busy={busy}
          disabled={text.trim() === ""}
          onClick={() => onConfirm(text)}
        >
          {confirmLabel}
        </Button>
      </div>
    </section>
  );
}
