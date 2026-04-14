import { useState, useEffect } from "react";
import { auth, audit } from "@/lib/api";
import { fmtDate } from "@/lib/utils";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { Users, ScrollText, Plus, Trash2, Shield } from "lucide-react";

type Tab = "users" | "logs";

export default function Admin() {
  const [tab, setTab] = useState<Tab>("users");
  const [users, setUsers] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ username: "", email: "", password: "", password_confirm: "", role: "viewer" });
  const [err, setErr] = useState("");

  const loadUsers = async () => { const { data } = await auth.users(); setUsers(data.results ?? data); };
  const loadLogs  = async () => { const { data } = await audit.logs(); setLogs(data.results ?? data); };

  useEffect(() => { loadUsers(); }, []);
  useEffect(() => { if (tab === "logs") loadLogs(); }, [tab]);

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await auth.createUser(form);
      setForm({ username: "", email: "", password: "", password_confirm: "", role: "viewer" });
      loadUsers();
    } catch (e: any) {
      setErr(JSON.stringify(e.response?.data ?? "Erro"));
    } finally {
      setLoading(false);
    }
  };

  const deleteUser = async (id: number) => {
    if (!confirm("Remover usuário?")) return;
    await auth.deleteUser(id);
    loadUsers();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-blue-500" />
          <div>
            <h2 className="text-xl font-bold text-white">Painel Administrativo</h2>
            <p className="text-sm text-[var(--muted)]">Usuários e logs de auditoria</p>
          </div>
        </div>
        <div className="flex gap-2">
          {(["users", "logs"] as Tab[]).map(t => (
            <Button key={t} variant={tab === t ? "primary" : "secondary"} onClick={() => setTab(t)}>
              {t === "users" ? <><Users className="w-4 h-4" /> Usuários</> : <><ScrollText className="w-4 h-4" /> Logs</>}
            </Button>
          ))}
        </div>
      </div>

      {tab === "users" && (
        <div className="space-y-5">
          {/* Create form */}
          <Card>
            <CardHeader><Plus className="w-4 h-4 text-blue-500" /><span className="text-sm font-semibold text-white">Novo Usuário</span></CardHeader>
            <CardBody>
              <form onSubmit={createUser} className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <Input placeholder="Usuário" value={form.username} onChange={e => setForm(p => ({ ...p, username: e.target.value }))} required />
                <Input placeholder="E-mail" type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
                <Input placeholder="Senha" type="password" value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} required />
                <Input placeholder="Confirmar senha" type="password" value={form.password_confirm} onChange={e => setForm(p => ({ ...p, password_confirm: e.target.value }))} required />
                <select value={form.role} onChange={e => setForm(p => ({ ...p, role: e.target.value }))}
                  className="bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
                  <option value="viewer">Visualizador</option>
                  <option value="analyst">Analista</option>
                  <option value="admin">Admin</option>
                </select>
                <Button type="submit" loading={loading}><Plus className="w-4 h-4" /> Criar</Button>
              </form>
              {err && <p className="text-xs text-red-400 mt-2">{err}</p>}
            </CardBody>
          </Card>

          {/* Users table */}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-xs text-[var(--muted)]">
                    <th className="text-left px-4 py-3 font-medium">Usuário</th>
                    <th className="text-left px-4 py-3 font-medium">Perfil</th>
                    <th className="text-left px-4 py-3 font-medium hidden sm:table-cell">Criado em</th>
                    <th className="text-right px-4 py-3 font-medium">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id} className="border-b border-[var(--border)]/50 hover:bg-white/2 transition-colors">
                      <td className="px-4 py-3 font-mono text-sm text-white">{u.username}</td>
                      <td className="px-4 py-3">
                        <Badge color={u.role === "admin" ? "blue" : "gray"}>{u.role}</Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-[var(--muted)] hidden sm:table-cell">{fmtDate(u.created_at)}</td>
                      <td className="px-4 py-3 text-right">
                        {u.username !== "admin" && (
                          <Button variant="danger" className="p-1.5" onClick={() => deleteUser(u.id)}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {tab === "logs" && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted)]">
                  <th className="text-left px-4 py-3 font-medium">Data/Hora</th>
                  <th className="text-left px-4 py-3 font-medium">Usuário</th>
                  <th className="text-left px-4 py-3 font-medium">Ação</th>
                  <th className="text-left px-4 py-3 font-medium">Detalhes</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr><td colSpan={4} className="text-center py-8 text-[var(--muted)]">Nenhum log encontrado</td></tr>
                ) : logs.map(l => (
                  <tr key={l.id} className="border-b border-[var(--border)]/50 hover:bg-white/2 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-[var(--muted)] whitespace-nowrap">{fmtDate(l.timestamp)}</td>
                    <td className="px-4 py-3 font-mono text-sm text-white">{l.username}</td>
                    <td className="px-4 py-3"><Badge color="gray">{l.action}</Badge></td>
                    <td className="px-4 py-3 text-sm text-[var(--text)]">{l.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
