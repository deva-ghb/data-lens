import { useGet } from "../api/hooks";

export type ShiftRef = { id: number; date: string; kind: "day" | "night"; start_at: string; label: string };
export type Meta = {
  site_now: string;
  site_now_local: string;
  current_shift: ShiftRef | null;
  next_shift: ShiftRef | null;
  focus_shift: ShiftRef | null;
  ai_available: boolean;
};

export function useMeta() {
  return useGet<Meta>("/api/meta", { refetchInterval: 20_000 });
}

/** "Tue 28 Jul, 18:00" from a local ISO time string. */
export function siteTime(localIso: string): string {
  const d = new Date(localIso);
  const day = d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short" });
  const time = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return `${day}, ${time}`;
}

/** A stored UTC time shown as site local time (UTC+4). */
export function localTime(utcIso: string, withDate = true): string {
  const d = new Date(new Date(utcIso + "Z").getTime() + 4 * 3600_000);
  const time = `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
  if (!withDate) return time;
  const day = d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", timeZone: "UTC" });
  return `${day}, ${time}`;
}
