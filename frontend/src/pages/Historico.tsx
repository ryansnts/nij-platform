import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { docs } from "@/lib/api";
import { fmtDate } from "@/lib/utils";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { FileText, Eye, Trash2, RefreshCw, Upload } from "lucide-react";

const STATUS: Record<string, { label: string; color: "gray" | "blue" | "green" | "red" | "yellow" }> = {
  pending:    { label: "Pendente",    color: "gray" },
  processing: { label: "Processando", color: "blue" },
  completed:  { label: "Concluído",   color: "green" },
  error:      { label: "Erro",        color: "red" },
};

export default function Historico() {
  const nav = useNavigate();
  const [list, setList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await docs.list();
      setList(data.results ?? data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const remove = async (id: string) => {
    if (!confirm("Remover este documento?")) return;
    await docs.remove(id);
    load();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Histórico de Análises</h2>
          <p className="text-sm text-[var(--muted)] mt-0.5">Todos os documentos processados</p>
        </div>
        <Button variant="secondary" onClick={load}>
          <RefreshCw className="w-4 h-4" /> Atualizar
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>
      ) : list.length === 0 ? (
        <div className="surface rounded-xl p-12 text-center space-y-4">
          <FileText className="w-10 h-10 text-[var(--muted)] mx-auto" />
          <p className="text-[var(--muted)] text-sm">Nenhum documento processado ainda.</p>
          <Button onClick={() => nav("/")}>
            <Upload className="w-4 h-4" /> Fazer upload
          </Button>
        </div>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted)]">
                  <th className="text-left px-4 py-3 font-medium">Arquivo</th>
                  <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Perfil</th>
                  <th className="text-left px-4 py-3 font-medium hidden sm:table-cell">Enviado em</th>
                  <th className="text-center px-4 py-3 font-medium">Status</th>
                  <th className="text-right px-4 py-3 font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {list.map((d) => {
                  const s = STATUS[d.status] ?? STATUS.pending;
                  return (
                    <tr key={d.id} className="border-b border-[var(--border)]/50 hover:bg-white/2 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-blue-500 shrink-0" />
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-white truncate max-w-[200px]">{d.original_filename}</p>
                            <p className="text-xs text-[var(--muted)]">{(d.file_size / 1024).toFixed(0)} KB</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-[var(--muted)] hidden md:table-cell">{d.extraction_profile}</td>
                      <td className="px-4 py-3 text-xs text-[var(--muted)] hidden sm:table-cell whitespace-nowrap">{fmtDate(d.created_at)}</td>
                      <td className="px-4 py-3 text-center">
                        <Badge color={s.color}>{s.label}</Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-1">
                          {d.status === "completed" && (
                            <Button variant="ghost" className="p-1.5" onClick={() => nav(`/resultado/${d.id}`)}>
                              <Eye className="w-4 h-4 text-blue-400" />
                            </Button>
                          )}
                          <Button variant="ghost" className="p-1.5" onClick={() => remove(d.id)}>
                            <Trash2 className="w-4 h-4 text-red-400" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
