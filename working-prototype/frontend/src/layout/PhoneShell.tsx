import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, House, LogOut, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { apiSend } from "../api/client";
import type { Me } from "../auth/useMe";
import { DataLensLogo } from "../brand/DataLensLogo";
import { siteTime, useMeta } from "./Meta";
import "./phone.css";

export function PhoneShell({ me, children }: { me: Me; children: ReactNode }) {
  const meta = useMeta();
  const navigate = useNavigate();
  const client = useQueryClient();
  const signOut = async () => {
    await apiSend("POST", "/api/auth/logout");
    client.clear();
    navigate("/login");
  };
  const home = me.role === "foreman" ? "/m/foreman" : "/m";
  return (
    <div className="phone">
      <div className="phone__frame">
        <header className="phone__top">
          <DataLensLogo size={24} />
          <span className="phone__time num">{meta.data ? siteTime(meta.data.site_now_local) : ""}</span>
          <button className="phone__out" type="button" onClick={signOut} aria-label="Sign out">
            <LogOut size={18} />
          </button>
        </header>
        <main className="phone__body">{children}</main>
        <nav className="phone__nav" aria-label="Phone navigation">
          <NavLink to={home} end className={({ isActive }) => (isActive ? "phone__tab phone__tab--on" : "phone__tab")}>
            <House aria-hidden="true" />
            <span>Today</span>
          </NavLink>
          <NavLink to="/m/report" className={({ isActive }) => (isActive ? "phone__tab phone__tab--on" : "phone__tab")}>
            <TriangleAlert aria-hidden="true" />
            <span>Report</span>
          </NavLink>
          <NavLink to="/m/cards" className={({ isActive }) => (isActive ? "phone__tab phone__tab--on" : "phone__tab")}>
            <BookOpen aria-hidden="true" />
            <span>Cards</span>
          </NavLink>
        </nav>
      </div>
    </div>
  );
}
