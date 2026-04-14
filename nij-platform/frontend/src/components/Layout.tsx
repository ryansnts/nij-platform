import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  FileText, Upload, History, Shield, LogOut, Calculator,
  ChevronLeft, ChevronRight, ReceiptText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

const navItems = [
  { to: "/", icon: Upload, label: "Upload" },
  { to: "/historico", icon: History, label: "Histórico" },
  { to: "/apendice01", icon: Calculator, label: "Apêndice 01" },
  { to: "/apendice02", icon: ReceiptText, label: "Apêndice 02" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { me, logout } = useAuth();
  const { pathname } = useLocation();
  const nav = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = async () => {
    await logout();
    nav("/login");
  };

  // Verificar se estamos numa rota de resultado/extrato
  const isResultado = pathname.startsWith("/resultado/");

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg)" }}>
      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside
        className={cn(
          "fixed top-0 left-0 h-screen z-50 flex flex-col border-r border-[var(--border)] bg-[var(--surface)] transition-all duration-200",
          collapsed ? "w-16" : "w-56"
        )}
      >
        {/* Brand */}
        <div className="h-14 flex items-center gap-2.5 px-3 border-b border-[var(--border)] shrink-0">
          <div className="w-8 h-8 rounded-lg bg-blue-600/10 border border-blue-500/20 flex items-center justify-center shrink-0">
            <FileText className="w-4 h-4 text-blue-500" />
          </div>
          {!collapsed && (
            <span className="font-semibold text-white text-sm truncate">
              NIJ · <span className="gradient-text">Jurídica</span>
            </span>
          )}
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
          {/* Extrato fixo no topo */}
          {isResultado && (
            <div
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm",
                "bg-emerald-600/10 text-emerald-400 border border-emerald-500/20"
              )}
            >
              <FileText className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="truncate font-medium">Extrato Bancário</span>}
            </div>
          )}

          {navItems.map(({ to, icon: Icon, label }) => {
            const active = pathname === to;
            return (
              <Link
                key={to}
                to={to}
                title={collapsed ? label : undefined}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
                  active
                    ? "bg-blue-600/10 text-blue-400 border border-blue-500/20"
                    : "text-[var(--muted)] hover:text-white hover:bg-white/5 border border-transparent"
                )}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!collapsed && <span className="truncate">{label}</span>}
              </Link>
            );
          })}

          {me?.role === "admin" && (
            <Link
              to="/admin"
              title={collapsed ? "Admin" : undefined}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
                pathname === "/admin"
                  ? "bg-blue-600/10 text-blue-400 border border-blue-500/20"
                  : "text-[var(--muted)] hover:text-white hover:bg-white/5 border border-transparent"
              )}
            >
              <Shield className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="truncate">Admin</span>}
            </Link>
          )}
        </nav>

        {/* Footer da sidebar */}
        <div className="border-t border-[var(--border)] p-2 space-y-1 shrink-0">
          {/* Usuário */}
          {!collapsed && (
            <div className="px-3 py-1.5">
              <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider">Usuário</p>
              <p className="text-xs text-white font-mono truncate">{me?.username}</p>
            </div>
          )}

          {/* Logout */}
          <button
            onClick={handleLogout}
            title="Sair"
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-[var(--muted)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            {!collapsed && <span>Sair</span>}
          </button>

          {/* Toggle collapse */}
          <button
            onClick={() => setCollapsed(c => !c)}
            className="w-full flex items-center justify-center py-1.5 rounded-lg text-[var(--muted)] hover:text-white hover:bg-white/5 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────── */}
      <div
        className={cn(
          "flex-1 flex flex-col min-h-screen transition-all duration-200",
          collapsed ? "ml-16" : "ml-56"
        )}
      >
        <main className="flex-1 w-full max-w-7xl mx-auto px-5 py-5">
          {children}
        </main>

        <footer className="border-t border-[var(--border)] py-3 text-center text-xs text-[var(--muted)]">
          NIJ — Núcleo de Inteligência Jurídica · GAC © 2026
        </footer>
      </div>
    </div>
  );
}
