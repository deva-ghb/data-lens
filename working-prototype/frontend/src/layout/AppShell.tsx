import { useQueryClient } from "@tanstack/react-query";
import { Clock3, LogOut, Menu as MenuIcon, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { apiSend } from "../api/client";
import { ROLE_LABEL, type Me } from "../auth/useMe";
import { DataLensLogo } from "../brand/DataLensLogo";
import { MirsalLogo } from "../brand/MirsalLogo";
import { Button } from "../ui/Button";
import { Menu } from "../ui/Menu";
import { siteTime, useMeta } from "./Meta";
import { navFor } from "./nav";
import "./layout.css";

function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("");
}

export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const meta = useMeta();
  const navigate = useNavigate();
  const client = useQueryClient();
  const signOut = async () => {
    await apiSend("POST", "/api/auth/logout");
    client.clear();
    navigate("/login");
  };
  return (
    <div className="shell">
      <aside className={open ? "shell__side shell__side--open" : "shell__side"} aria-label="Main navigation">
        <div className="shell__brand">
          <DataLensLogo size={28} />
          <Button variant="ghost" iconOnly aria-label="Close menu" className="shell__close" onClick={() => setOpen(false)} icon={<X />} />
        </div>
        <nav className="shell__nav">
          {navFor(me.role).map((group) => (
            <div className="shell__group" key={group.label}>
              <span className="shell__group-label">{group.label}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) => (isActive ? "shell__link shell__link--active" : "shell__link")}
                  onClick={() => setOpen(false)}
                >
                  <item.icon aria-hidden="true" />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="shell__org">
          <MirsalLogo size={22} />
        </div>
      </aside>
      {open && <div className="shell__scrim" onClick={() => setOpen(false)} aria-hidden="true" />}
      <div className="shell__main">
        <header className="shell__top">
          <Button variant="ghost" iconOnly aria-label="Open menu" className="shell__burger" onClick={() => setOpen(true)} icon={<MenuIcon />} />
          <div className="shell__clock" title="Site time, Abu Dhabi (UTC+4)">
            <Clock3 aria-hidden="true" />
            <span className="shell__clock-label">Site time</span>
            <span className="num">{meta.data ? siteTime(meta.data.site_now_local) : "…"}</span>
          </div>
          {meta.data?.focus_shift && (
            <span className="shell__shift">Planning for {meta.data.focus_shift.label}</span>
          )}
          <div className="shell__spacer" />
          <Menu
            label="Account"
            trigger={
              <button className="shell__user" type="button">
                <span className="shell__avatar" aria-hidden="true">
                  {initials(me.name)}
                </span>
                <span className="shell__who">
                  <span className="shell__name">{me.name}</span>
                  <span className="shell__role">{ROLE_LABEL[me.role]}</span>
                </span>
              </button>
            }
            items={[{ label: "Sign out", icon: <LogOut />, onSelect: signOut }]}
          />
        </header>
        <main className="shell__content">{children}</main>
      </div>
    </div>
  );
}

export function Page({
  title,
  subtitle,
  actions,
  children,
  wide = false,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "page page--wide" : "page"}>
      <div className="page__head">
        <div className="page__titles">
          <h1>{title}</h1>
          {subtitle && <p className="page__subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="page__actions">{actions}</div>}
      </div>
      {children}
    </div>
  );
}
