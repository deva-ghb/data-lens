import { useGet } from "../api/hooks";

export type Role =
  | "worker"
  | "foreman"
  | "planner"
  | "shift_manager"
  | "permit_issuer"
  | "hse_head"
  | "clinician"
  | "authority"
  | "admin";

export type Me = {
  id: number;
  name: string;
  role: Role;
  employer: string;
  email: string;
  display_language: string;
};

export const ROLE_LABEL: Record<Role, string> = {
  worker: "Worker",
  foreman: "Foreman",
  planner: "Planner",
  shift_manager: "Shift manager",
  permit_issuer: "Permit issuer",
  hse_head: "Head of HSE",
  clinician: "Occupational health",
  authority: "District authority",
  admin: "Administrator",
};

export const PHONE_ROLES: Role[] = ["worker", "foreman"];

export function useMe() {
  return useGet<Me>("/api/auth/me", { retry: false, staleTime: 60_000 });
}
