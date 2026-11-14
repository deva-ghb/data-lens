import { UserPlus } from "lucide-react";
import { useState } from "react";
import { useGet, useSend } from "../../api/hooks";
import { ROLE_LABEL, type Role } from "../../auth/useMe";
import { Page } from "../../layout/AppShell";
import { Button } from "../../ui/Button";
import { Card } from "../../ui/Card";
import { Dialog } from "../../ui/Dialog";
import { Field, Input } from "../../ui/Field";
import { Select } from "../../ui/Select";
import { Table, type Column } from "../../ui/Table";
import { useToast } from "../../ui/Toast";
import { Loaded } from "../common";
import "../pages.css";

type PersonRow = { id: number; name: string; email: string; role: Role; employer: string | null; job_title: string; camp: string | null; active: boolean };
const ROLES = Object.entries(ROLE_LABEL).map(([value, label]) => ({ value, label }));
const EMPLOYERS = ["Mirsal Terminals", "Sahel Marine Services", "Bayan Manpower Contracting"];

export function People() {
  const [q, setQ] = useState("");
  const [role, setRole] = useState("all");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const list = useGet<{ total: number; page: number; page_size: number; people: PersonRow[] }>(`/api/admin/people?q=${encodeURIComponent(q)}&page=${page}${role !== "all" ? `&role=${role}` : ""}`);
  const columns: Column<PersonRow>[] = [
    { key: "name", header: "Name", render: (p) => <span className="stack stack--tight"><strong className="small">{p.name}</strong><span className="xsmall muted">{p.email}</span></span> },
    { key: "role", header: "Role", render: (p) => ROLE_LABEL[p.role], width: 170 },
    { key: "employer", header: "Employer", render: (p) => p.employer, width: 220 },
    { key: "job", header: "Job", render: (p) => <span className="small">{p.job_title}</span>, width: 220 },
    { key: "active", header: "Status", render: (p) => <span className={p.active ? "pill pill--mint" : "pill"}>{p.active ? "Active" : "Off"}</span>, width: 100 },
  ];
  return (
    <Page title="People" subtitle="Onboard people and set their role. Every account starts with the password welcome@123." actions={<Button variant="primary" icon={<UserPlus />} onClick={() => setOpen(true)}>Onboard a person</Button>}>
      <Loaded query={list}>
        {(data) => (
          <Card
            flush
            title={`${data.total} people`}
            actions={
              <div className="row">
                <Input aria-label="Search people" placeholder="Search name or email" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} className="filter-input" />
                <Select aria-label="Role" value={role} onValueChange={(v) => { setRole(v); setPage(1); }} options={[{ value: "all", label: "All roles" }, ...ROLES]} />
              </div>
            }
          >
            <Table caption="People" columns={columns} rows={data.people} rowKey={(p) => String(p.id)} />
            <div className="row row--between" style={{ padding: 16 }}>
              <span className="small muted">Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))}</span>
              <div className="row">
                <Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
                <Button size="sm" disabled={page * data.page_size >= data.total} onClick={() => setPage(page + 1)}>Next</Button>
              </div>
            </div>
          </Card>
        )}
      </Loaded>
      <Onboard open={open} onOpenChange={setOpen} />
    </Page>
  );
}

function Onboard({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [form, setForm] = useState({ first_name: "", last_name: "", role: "worker", employer: EMPLOYERS[0] ?? "", job_title: "" });
  const save = useSend<typeof form, { email: string }>("POST", "/api/admin/people");
  const toast = useToast();
  const ok = form.first_name.trim() && form.last_name.trim() && form.job_title.trim();
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Onboard a person"
      footer={
        <>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button variant="primary" disabled={!ok} busy={save.isPending} onClick={() => save.mutate(form, { onSuccess: (r) => { onOpenChange(false); toast({ title: "Account created", body: `${r.email} can sign in with welcome@123.`, tone: "good" }); }, onError: (e) => toast({ title: "Not created", body: e.message, tone: "critical" }) })}>
            Create account
          </Button>
        </>
      }
    >
      <div className="grid grid--2">
        <Field label="First name">{(p) => <Input {...p} value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />}</Field>
        <Field label="Last name">{(p) => <Input {...p} value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />}</Field>
        <Field label="Role">{(p) => <Select {...p} value={form.role} onValueChange={(role) => setForm({ ...form, role })} options={ROLES} />}</Field>
        <Field label="Employer">{(p) => <Select {...p} value={form.employer} onValueChange={(employer) => setForm({ ...form, employer })} options={EMPLOYERS.map((e) => ({ value: e, label: e }))} />}</Field>
        <Field label="Job title" className="span-2">{(p) => <Input {...p} value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />}</Field>
      </div>
    </Dialog>
  );
}
