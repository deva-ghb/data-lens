import { Camera, Send } from "lucide-react";
import { useState } from "react";
import { useSend } from "../../api/hooks";
import { Button } from "../../ui/Button";
import { Field } from "../../ui/Field";
import { Select } from "../../ui/Select";
import { TextArea } from "../../ui/TextArea";
import { useToast } from "../../ui/Toast";
import "../pages.css";

const ZONES = ["Berth 1", "Berth 2", "Berth 3", "Berth 4", "Yard Block 1", "Yard Block 2", "Yard Block 3", "Yard Block 4", "Yard Block 5", "Yard Block 6", "Workshop Area", "Gate Complex", "Camp Block A", "Camp Block B", "Camp Block C", "Camp Block D", "Camp Block E"];
const WORK: [string, string][] = [["", "No work involved (a hazard)"], ["LASH_DECK", "Lashing at height"], ["TWIST_GROUND", "Ground twist-locks"], ["MOORING", "Mooring"], ["TT_DRIVING", "Tractor driving"], ["REACH_STACKER", "Reach stacker"], ["QC_OPS", "Quay crane"]];

export function PhoneReport() {
  const [text, setText] = useState("");
  const [zone, setZone] = useState("Berth 2");
  const [work, setWork] = useState("LASH_DECK");
  const [photo, setPhoto] = useState<string | null>(null);
  const send = useSend<{ text: string; zone: string; activity_code: string | null; photo: string | null }, { kind: string }>("POST", "/api/incidents");
  const toast = useToast();
  const pick = (file: File | undefined) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setPhoto(String(reader.result));
    reader.readAsDataURL(file);
  };
  return (
    <>
      <h1 className="phone-title">Report something</h1>
      <p className="small muted">A few words is enough. The copilot drafts the record and the safety team confirms it.</p>
      <div className="phone-card">
        <Field label="What happened?">{(p) => <TextArea {...p} rows={4} value={text} onChange={(e) => setText(e.target.value)} placeholder="For example: lasher slipped on the bay 14 ladder, harness caught him" />}</Field>
        <Field label="Where?">{(p) => <Select {...p} value={zone} onValueChange={setZone} options={ZONES.map((z) => ({ value: z, label: z }))} />}</Field>
        <Field label="What work?">{(p) => <Select {...p} value={work || "none"} onValueChange={(v) => setWork(v === "none" ? "" : v)} options={WORK.map(([v, l]) => ({ value: v || "none", label: l }))} />}</Field>
        <label className="tap" style={{ gap: 8 }}>
          <Camera size={18} aria-hidden="true" /> {photo ? "Photo added" : "Add a photo"}
          <input type="file" accept="image/*" capture="environment" hidden onChange={(e) => pick(e.target.files?.[0])} />
        </label>
        {photo && <img src={photo} alt="Your photo" style={{ width: "100%", borderRadius: 8, maxHeight: 220, objectFit: "cover" }} />}
        <Button
          variant="primary"
          block
          icon={<Send />}
          disabled={text.trim().length < 5}
          busy={send.isPending}
          onClick={() => send.mutate({ text, zone, activity_code: work || null, photo }, { onSuccess: () => { setText(""); setPhoto(null); toast({ title: "Report sent", body: "Thank you. The safety team has it.", tone: "good" }); }, onError: (e) => toast({ title: "Not sent", body: e.message, tone: "critical" }) })}
          style={{ minHeight: 52 }}
        >
          Send report
        </Button>
      </div>
    </>
  );
}
