import {
  Activity,
  BookOpen,
  CalendarClock,
  ClipboardCheck,
  ClipboardList,
  FileCheck2,
  FlaskConical,
  Gauge,
  House,
  Landmark,
  ListChecks,
  Radar,
  Radio,
  ScrollText,
  ShieldCheck,
  Stethoscope,
  TrendingUp,
  Users,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import type { Role } from "../auth/useMe";

export type NavItem = { to: string; label: string; icon: LucideIcon; roles: Role[] };
export type NavGroup = { label: string; items: NavItem[] };

const STAFF: Role[] = ["planner", "shift_manager", "permit_issuer", "hse_head"];

export const NAV: NavGroup[] = [
  { label: "Today", items: [{ to: "/", label: "Home", icon: House, roles: [...STAFF, "clinician", "authority", "admin"] }] },
  {
    label: "Shift",
    items: [
      { to: "/roster", label: "Assignment risk", icon: Gauge, roles: ["planner", "hse_head"] },
      { to: "/swaps", label: "Swaps to approve", icon: UsersRound, roles: ["shift_manager"] },
      { to: "/permits", label: "Permits to work", icon: FileCheck2, roles: ["planner", "shift_manager", "permit_issuer", "hse_head"] },
    ],
  },
  {
    label: "Early warning",
    items: [
      { to: "/warnings", label: "Early warnings", icon: Radar, roles: ["hse_head"] },
      { to: "/district", label: "District view", icon: Landmark, roles: ["hse_head", "authority"] },
    ],
  },
  {
    label: "Safety records",
    items: [
      { to: "/reports", label: "Incidents and hazards", icon: ClipboardList, roles: ["hse_head"] },
      { to: "/inspections", label: "Inspections", icon: ClipboardCheck, roles: ["hse_head"] },
      { to: "/actions", label: "Actions", icon: ListChecks, roles: ["hse_head", "planner"] },
      { to: "/learning", label: "Learning", icon: BookOpen, roles: ["hse_head"] },
    ],
  },
  {
    label: "Register",
    items: [
      { to: "/activities", label: "Activities", icon: Activity, roles: STAFF },
      { to: "/groups", label: "Behavioural groups", icon: Users, roles: ["hse_head", "planner"] },
    ],
  },
  { label: "Health", items: [{ to: "/health", label: "Screening", icon: Stethoscope, roles: ["clinician"] }] },
  {
    label: "Analytics",
    items: [
      { to: "/validation", label: "Validation", icon: FlaskConical, roles: ["hse_head"] },
      { to: "/impact", label: "Impact", icon: TrendingUp, roles: ["hse_head"] },
    ],
  },
  {
    label: "Governance",
    items: [
      { to: "/governance", label: "Governance", icon: ShieldCheck, roles: ["hse_head", "admin", "authority"] },
      { to: "/audit", label: "Audit trail", icon: ScrollText, roles: ["hse_head", "admin", "authority"] },
      { to: "/signals", label: "Signals", icon: Radio, roles: ["hse_head", "admin"] },
    ],
  },
  {
    label: "Administration",
    items: [
      { to: "/admin/people", label: "People", icon: Users, roles: ["admin"] },
      { to: "/admin/clock", label: "Site clock", icon: CalendarClock, roles: ["admin"] },
    ],
  },
];

export function navFor(role: Role): NavGroup[] {
  return NAV.map((g) => ({ ...g, items: g.items.filter((i) => i.roles.includes(role)) })).filter((g) => g.items.length > 0);
}
