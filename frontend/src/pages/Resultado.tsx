import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { docs } from "@/lib/api";
import { brl, fmtDate } from "@/lib/utils";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { ArrowLeft, Download, User, Building, CreditCard, Calendar, TrendingUp, AlertTriangle, RefreshCw } from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import Extrato, { type ExtratoLinha } from "./Extrato";

export default function Resultado() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [doc, setDoc] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [reprocessing, setReprocessing] = useState(false);

  const fetchDoc = async () => {
    if (!id) return;
    const { data } = await docs.get(id);
    setDoc(data);
    if (data.status === "processing" || data.status === "pending") {
      setTimeout(fetchDoc, 3000);
    } else {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoc().catch(() => setLoading(false));
  }, [id]);

  const handleReprocess = async () => {
    if (!id) return;
    setReprocessing(true);
    setLoading(true);
    try {
      await docs.reprocess(id);
      fetchDoc();
    } catch (err) {
      console.error("Erro ao reprocessar:", err);
      setLoading(false);
    }
    setReprocessing(false);
  };

  const exportCSV = () => {
    const t = doc?.analysis?.transacoes ?? [];
    if (!t.length) return;
    const rows = [["Data","Descrição","Valor","Tipo"], ...t.map((x: any) => [x.data, x.descricao, x.valor, x.tipo])];
    const csv = rows.map(r => r.map(String).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `nij-${doc.original_filename}.csv`;
    a.click();
  };

  if (loading || doc?.status === "processing" || doc?.status === "pending") {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Spinner className="w-10 h-10" />
        <p className="text-[var(--muted)] text-sm">Processando documento...</p>
      </div>
    );
  }

  if (!doc || doc.status === "error") {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <AlertTriangle className="w-10 h-10 text-red-500" />
        <p className="text-white font-medium">Erro no processamento</p>
        <p className="text-sm text-[var(--muted)]">{doc?.error_message}</p>
        <Button variant="secondary" onClick={() => nav("/")}>Voltar</Button>
      </div>
    );
  }

  const a = doc.analysis;

  // ── Função para exportar dados para os Apêndices ──
  const handleExportToApendice = (dados: ExtratoLinha[], tipo: "apendice1" | "apendice2") => {
    nav(`/${tipo === "apendice1" ? "apendice01" : "apendice02"}`, { state: { dados } });
  };

  // ── Detectar formatos que usam a tela de Extrato com filtros ──
  // Verifica se raw_text é um JSON array — isso é o indicador definitivo
  // de que o processador retornou dados estruturados (linhas de extrato)
  const isExtratoFormat = (() => {
    const rawText = a?.raw_text ?? "";
    if (!rawText || rawText.length < 2) return false;
    // Verificação rápida: se começa com "[" é JSON array
    if (rawText.trimStart().startsWith("[")) {
      try {
        const parsed = JSON.parse(rawText);
        return Array.isArray(parsed) && parsed.length > 0;
      } catch {
        return false;
      }
    }
    return false;
  })();
  
  if (isExtratoFormat) {
    let linhas: ExtratoLinha[] = [];
    try { linhas = JSON.parse(a?.raw_text ?? "[]"); } catch { linhas = a?.transacoes?.map((t: any) => ({
      data: t.data, descricao: t.descricao,
      debito: t.tipo === "debito" ? t.valor : 0,
      credito: t.tipo === "credito" ? t.valor : 0,
      tipo: t.tipo,
    })) ?? []; }
    return (
      <Extrato
        linhas={linhas}
        nome={a?.nome}
        orgao={a?.orgao}
        competencia={a?.competencia}
        fileName={doc.original_filename}
        onReprocess={handleReprocess}
        reprocessing={reprocessing}
        onExportToApendice={handleExportToApendice}
      />
    );
  }

  const margem = [
    { name: "Utilizada", value: parseFloat(a?.margem_utilizada ?? "0") || 0, color: "#f85149" },
    { name: "Disponível", value: parseFloat(a?.margem_disponivel ?? "0") || 0, color: "#3fb950" },
  ];
  const temMargem = margem[0].value + margem[1].value > 0;

  return (
    <div className="space-y-5">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => nav("/historico")} className="p-2">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h2 className="text-lg font-bold text-white">Resultado da Análise</h2>
            <p className="text-xs text-[var(--muted)] font-mono">{doc.original_filename}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleReprocess} disabled={reprocessing}>
            <RefreshCw className={`w-4 h-4 ${reprocessing ? "animate-spin" : ""}`} /> Reprocessar
          </Button>
          <Button variant="secondary" onClick={exportCSV}>
            <Download className="w-4 h-4" /> Exportar CSV
          </Button>
        </div>
      </div>

      {/* Info pessoal */}
      {a && (
        <Card>
          <CardHeader>
            <User className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-semibold text-white">Informações do Servidor</span>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { icon: User, label: "Nome", value: a.nome || "—" },
                { icon: CreditCard, label: "CPF", value: a.cpf || "—" },
                { icon: Building, label: "Órgão", value: a.orgao || "—" },
                { icon: Calendar, label: "Competência", value: a.competencia || "—" },
              ].map(({ icon: Icon, label, value }) => (
                <div key={label}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon className="w-3.5 h-3.5 text-[var(--muted)]" />
                    <span className="text-xs text-[var(--muted)]">{label}</span>
                  </div>
                  <p className="text-sm font-medium text-white truncate">{value}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-[var(--border)]">
              {[
                { label: "Valor Bruto", value: brl(a.valor_bruto), color: "text-blue-400" },
                { label: "Valor Líquido", value: brl(a.valor_liquido), color: "text-green-400" },
                { label: "Margem Disponível", value: brl(a.margem_disponivel), color: "text-yellow-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center">
                  <p className="text-xs text-[var(--muted)] mb-1">{label}</p>
                  <p className={`text-base font-bold font-mono ${color}`}>{value}</p>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Margem + Descontos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {temMargem && (
          <Card>
            <CardHeader>
              <TrendingUp className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-semibold text-white">Margem Consignável</span>
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={margem} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                    {margem.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => `R$ ${brl(v)}`}
                    contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-3 mt-2">
                {margem.map(m => (
                  <div key={m.name} className="text-center p-2 rounded-lg bg-white/3 border border-[var(--border)]">
                    <p className="text-xs text-[var(--muted)]">{m.name}</p>
                    <p className="font-mono text-sm font-bold mt-0.5" style={{ color: m.color }}>R$ {brl(m.value)}</p>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        )}

        {a?.descontos_indevidos?.length > 0 && (
          <Card>
            <CardHeader>
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span className="text-sm font-semibold text-white">Descontos Indevidos</span>
              <span className="ml-auto font-mono text-sm font-bold text-red-400">
                R$ {brl(a.descontos_indevidos.reduce((s: number, d: any) => s + d.valor, 0))}
              </span>
            </CardHeader>
            <CardBody className="space-y-2">
              {a.descontos_indevidos.map((d: any, i: number) => (
                <div key={i} className="flex items-start justify-between gap-3 p-3 rounded-lg bg-white/3 border border-[var(--border)]">
                  <div className="min-w-0">
                    <p className="text-sm text-white truncate">{d.descricao}</p>
                    <Badge color={d.status === "confirmado" ? "red" : "yellow"} className="mt-1">{d.tipo}</Badge>
                  </div>
                  <span className="font-mono text-sm font-bold text-red-400 shrink-0">
                    {d.valor > 0 ? `R$ ${brl(d.valor)}` : "—"}
                  </span>
                </div>
              ))}
            </CardBody>
          </Card>
        )}
      </div>

      {/* Transações */}
      {a?.transacoes?.length > 0 && (
        <Card>
          <CardHeader>
            <span className="text-sm font-semibold text-white">Transações ({a.transacoes.length})</span>
            <div className="ml-auto flex gap-4 text-xs text-[var(--muted)]">
              <span>Débitos: <span className="text-red-400 font-mono font-semibold">
                R$ {brl(a.transacoes.filter((t: any) => t.tipo === "debito").reduce((s: number, t: any) => s + t.valor, 0))}
              </span></span>
              <span>Créditos: <span className="text-green-400 font-mono font-semibold">
                R$ {brl(a.transacoes.filter((t: any) => t.tipo === "credito").reduce((s: number, t: any) => s + t.valor, 0))}
              </span></span>
            </div>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted)]">
                  <th className="text-left px-4 py-3 font-medium">Data</th>
                  <th className="text-left px-4 py-3 font-medium">Descrição</th>
                  <th className="text-right px-4 py-3 font-medium">Valor</th>
                  <th className="text-center px-4 py-3 font-medium">Tipo</th>
                </tr>
              </thead>
              <tbody>
                {a.transacoes.map((t: any, i: number) => (
                  <tr key={i} className="border-b border-[var(--border)]/50 hover:bg-white/2 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-[var(--muted)] whitespace-nowrap">{t.data}</td>
                    <td className="px-4 py-3 text-white max-w-xs truncate">{t.descricao}</td>
                    <td className={`px-4 py-3 text-right font-mono font-semibold ${t.tipo === "debito" ? "text-red-400" : "text-green-400"}`}>
                      R$ {brl(t.valor)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Badge color={t.tipo === "debito" ? "red" : "green"}>{t.tipo}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Contratos */}
      {a?.contratos?.length > 0 && (
        <Card>
          <CardHeader>
            <CreditCard className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-semibold text-white">Contratos Consignados ({a.contratos.length})</span>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted)]">
                  <th className="text-left px-4 py-3 font-medium">Contrato</th>
                  <th className="text-left px-4 py-3 font-medium">Banco</th>
                  <th className="text-left px-4 py-3 font-medium">Tipo</th>
                  <th className="text-right px-4 py-3 font-medium">Parcela</th>
                  <th className="text-right px-4 py-3 font-medium">Saldo Devedor</th>
                  <th className="text-right px-4 py-3 font-medium">Taxa a.m.</th>
                </tr>
              </thead>
              <tbody>
                {a.contratos.map((c: any, i: number) => (
                  <tr key={i} className="border-b border-[var(--border)]/50 hover:bg-white/2 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-[var(--muted)]">{c.numero}</td>
                    <td className="px-4 py-3 text-white">{c.banco}</td>
                    <td className="px-4 py-3"><Badge color="blue">{c.tipo}</Badge></td>
                    <td className="px-4 py-3 text-right font-mono text-sm">R$ {brl(c.valorParcela)}</td>
                    <td className="px-4 py-3 text-right font-mono text-sm text-red-400">R$ {brl(c.saldoDevedor)}</td>
                    <td className={`px-4 py-3 text-right font-mono text-sm ${c.taxaJuros > 2.14 ? "text-red-400 font-bold" : "text-white"}`}>
                      {c.taxaJuros > 0 ? `${c.taxaJuros.toFixed(2)}%` : "—"}
                      {c.taxaJuros > 2.14 && " ⚠️"}
                    </td>
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
