import {
  BarChart3,
  BookOpen,
  CircleDollarSign,
  FlaskConical,
  LayoutDashboard,
  Menu,
  Settings,
  X,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import type { Page } from "../types";
import { Logo } from "./Logo";

const navigation: Array<{
  page: Page;
  label: string;
  icon: typeof LayoutDashboard;
}> = [
  { page: "overview", label: "Overview", icon: LayoutDashboard },
  { page: "playground", label: "RAG playground", icon: FlaskConical },
  { page: "knowledge", label: "Knowledge", icon: BookOpen },
  { page: "evaluations", label: "Evaluations", icon: BarChart3 },
  { page: "cost", label: "Cost model", icon: CircleDollarSign },
];

interface ShellProps {
  page: Page;
  onNavigate: (page: Page) => void;
  children: ReactNode;
  connection: "online" | "demo" | "offline";
}

export function Shell({ page, onNavigate, children, connection }: ShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navigate = (target: Page) => {
    onNavigate(target);
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "is-open" : ""}`}>
        <div className="sidebar-head">
          <Logo />
          <button
            className="icon-button sidebar-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X size={19} />
          </button>
        </div>
        <nav className="primary-nav" aria-label="Primary">
          <span className="nav-label">Workspace</span>
          {navigation.map(({ page: target, label, icon: Icon }) => (
            <button
              key={target}
              className={`nav-item ${page === target ? "active" : ""}`}
              onClick={() => navigate(target)}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <button
          className={`nav-item ${page === "settings" ? "active" : ""}`}
          onClick={() => navigate("settings")}
        >
          <Settings size={18} strokeWidth={1.8} />
          <span>Settings</span>
        </button>
        <div className="sidebar-status">
          <div className={`status-orb status-${connection}`} />
          <div>
            <strong>
              {connection === "online"
                ? "Live backend"
                : connection === "demo"
                  ? "Demo workspace"
                  : "Backend offline"}
            </strong>
            <span>
              {connection === "online"
                ? "Chroma connected"
                : connection === "demo"
                  ? "Safe, local sample data"
                  : "Check connection settings"}
            </span>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <button
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="content-frame">
        <header className="mobile-header">
          <button
            className="icon-button"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>
          <Logo compact />
          <div className={`status-orb status-${connection}`} />
        </header>
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
