import { useGet, useSend } from "../../api/hooks";
import { Button } from "../../ui/Button";
import { Loaded } from "../common";
import "../pages.css";

type Card_ = { id: number; content: string; read: boolean };

export function Cards() {
  const cards = useGet<Card_[]>("/api/learning/mine");
  return (
    <>
      <h1 className="phone-title">Safety cards</h1>
      <Loaded query={cards}>
        {(rows) => (
          <>
            {rows.length === 0 && <p className="small muted">No cards yet.</p>}
            {rows.map((c) => <CardItem key={c.id} card={c} />)}
          </>
        )}
      </Loaded>
    </>
  );
}

function CardItem({ card }: { card: Card_ }) {
  const read = useSend<Record<string, never>>("POST", `/api/learning/${card.id}/read`);
  return (
    <div className={card.read ? "phone-card" : "phone-card phone-card--tint"}>
      <p className="small">{card.content}</p>
      {card.read ? <span className="xsmall muted">Read</span> : <Button variant="secondary" busy={read.isPending} onClick={() => read.mutate({})}>I have read this</Button>}
    </div>
  );
}
