import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as XLSX from "xlsx";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  ArrowLeft, Download, Plus, X, Search, Tag,
  TrendingDown, TrendingUp, FileSpreadsheet, FileText, RefreshCw,
  ChevronDown, List, FileDown, Calculator, Check, Square, CheckSquare,
} from "lucide-react";
import { brl } from "@/lib/utils";

export interface ExtratoLinha {
  data: string;
  descricao: string;
  debito: number;
  credito: number;
  tipo: "debito" | "credito";
  competencia?: string; // Competência MM/AAAA (para contracheques e históricos)
}

interface Props {
  linhas: ExtratoLinha[];
  nome?: string;
  orgao?: string;
  competencia?: string;
  fileName: string;
  onReprocess?: () => void;
  reprocessing?: boolean;
  onExportToApendice?: (dados: ExtratoLinha[], tipo: "apendice1" | "apendice2") => void;
}

const LS_KEY_FILTROS = "nij_extrato_filtros";
const LS_KEY_TIPO_FILTRO = "nij_extrato_tipo_filtro";
const LS_KEY_DADOS_FILTRADOS = "nij_extrato_dados_filtrados";

// Normalizar descrição para comparação de filtros
// Mesma lógica usada no agrupamento de tipos de lançamentos
function normalizarDescricao(desc: string): string {
  return desc
    .toUpperCase()
    .replace(/\d{2}\/\d{2}\/\d{4}/g, "")
    .replace(/CONTR\s*\d+/gi, "CONTR")
    .replace(/PARC\s*\d+\/\d+/gi, "PARCELA")
    .replace(/\d{6,}/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

// Verificar se uma descrição bate com um filtro
function descricaoBateComFiltro(descricao: string, filtro: string): boolean {
  return descricao.toLowerCase().includes(filtro) || normalizarDescricao(descricao).includes(filtro);
}

function loadFiltros(): string[] {
  try {
    const raw = localStorage.getItem(LS_KEY_FILTROS);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return [];
}

function loadTipoFiltro(): "todos" | "debito" | "credito" {
  try {
    const raw = localStorage.getItem(LS_KEY_TIPO_FILTRO);
    if (raw && ["todos", "debito", "credito"].includes(raw)) return raw as "todos" | "debito" | "credito";
  } catch { /* ignore */ }
  return "todos";
}

export default function Extrato({ linhas, nome, orgao, competencia, fileName, onReprocess, reprocessing, onExportToApendice }: Props) {
  const nav = useNavigate();
  const [filtros, setFiltros] = useState<string[]>(loadFiltros);
  const [inputFiltro, setInputFiltro] = useState("");
  const [tipoFiltro, setTipoFiltro] = useState<"todos" | "debito" | "credito">(loadTipoFiltro);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [selectedTipos, setSelectedTipos] = useState<Set<string>>(new Set());

  // Persistir filtros no localStorage
  useEffect(() => {
    localStorage.setItem(LS_KEY_FILTROS, JSON.stringify(filtros));
  }, [filtros]);

  useEffect(() => {
    localStorage.setItem(LS_KEY_TIPO_FILTRO, tipoFiltro);
  }, [tipoFiltro]);

  // ── Verificar se há dados de competência (para contracheques e faturas) ───
  const hasCompetencia = useMemo(() => linhas.some(l => l.competencia), [linhas]);

  // ── Extrair tipos únicos de lançamentos ───────────────
  const tiposLancamentos = useMemo(() => {
    const tipos = new Map<string, { count: number; totalDebito: number; totalCredito: number; descricoes: Set<string> }>();
    
    linhas.forEach(l => {
      // Normalizar descrição para agrupar similares
      let descNorm = l.descricao
        .toUpperCase()
        .replace(/\[\d+\]\s*/g, "") // Remove códigos [1234]
        .replace(/\d{2}\/\d{2}\/\d{4}/g, "") // Remove datas
        .replace(/CONTR\s*\d+/gi, "CONTR") // Normaliza contratos
        .replace(/PARC\s*\d+\/\d+/gi, "PARCELA") // Normaliza parcelas
        .replace(/\d{6,}/g, "") // Remove números longos (códigos)
        .replace(/\s+/g, " ")
        .trim();
      
      // Extrair palavra-chave principal
      const keywords = [
        "INSS", "PARCELA CREDITO PESSOAL", "PARCELA CREDITO", "CARTAO CREDITO ANUIDADE",
        "TARIFA BANCARIA", "ENCARGOS LIMITE", "IOF", "SAQUE", "PIX", "TED", "DOC",
        "DEPOSITO", "SALARIO", "BENEFICIO", "TRANSFERENCIA", "BOLETO", "PAGAMENTO",
        "SEGURO", "TAXA", "JUROS", "ESTORNO", "DEVOLUCAO"
      ];
      
      let tipoKey = descNorm;
      for (const kw of keywords) {
        if (descNorm.includes(kw)) {
          tipoKey = kw;
          break;
        }
      }
      
      // Se não encontrou keyword, usar as primeiras palavras
      if (tipoKey === descNorm) {
        const words = descNorm.split(" ").filter(w => w.length > 2);
        tipoKey = words.slice(0, 3).join(" ") || descNorm;
      }
      
      const existing = tipos.get(tipoKey) || { count: 0, totalDebito: 0, totalCredito: 0, descricoes: new Set<string>() };
      existing.count += 1;
      existing.totalDebito += l.debito;
      existing.totalCredito += l.credito;
      existing.descricoes.add(l.descricao);
      tipos.set(tipoKey, existing);
    });
    
    // Ordenar por quantidade de ocorrências
    return Array.from(tipos.entries())
      .map(([nome, stats]) => ({ nome, ...stats, descricoes: Array.from(stats.descricoes) }))
      .sort((a, b) => b.count - a.count);
  }, [linhas]);

  // ── Adicionar filtro ──────────────────────────────────
  const addFiltro = (valor?: string) => {
    const f = (valor || inputFiltro).trim().toLowerCase();
    if (f && !filtros.includes(f)) {
      setFiltros(p => [...p, f]);
      setInputFiltro("");
    }
  };

  // ── Adicionar filtro a partir do dropdown de tipos ────
  // Encontra o menor trecho comum entre todas as descrições do grupo
  // para garantir que o filtro funcione com as descrições reais
  const addFiltroFromTipo = (tipoNome: string) => {
    const tipo = tiposLancamentos.find(t => t.nome === tipoNome);
    if (!tipo) return addFiltro(tipoNome);
    
    // Pegar a primeira descrição real (sem código [XXXX]) como base do filtro
    // Isso garante que o filtro bata com as transações reais
    const descs = tipo.descricoes.map(d => d.replace(/^\[\d+\]\s*/, "").trim().toLowerCase());
    
    if (descs.length === 1) {
      // Só tem uma descrição única — usar ela diretamente
      const f = descs[0];
      if (f && !filtros.includes(f)) {
        setFiltros(p => [...p, f]);
      }
      return;
    }
    
    // Múltiplas descrições — encontrar o maior prefixo comum
    // Ex: ["DESCONTO EM FOLHA P", "DESCONTO EM FOLHA PAGTO"] → "desconto em folha"
    let common = descs[0];
    for (let i = 1; i < descs.length; i++) {
      let j = 0;
      while (j < common.length && j < descs[i].length && common[j] === descs[i][j]) j++;
      common = common.substring(0, j);
    }
    // Cortar no último espaço para não ficar com palavra cortada
    const lastSpace = common.trimEnd().lastIndexOf(" ");
    const filtro = lastSpace > 2 ? common.substring(0, lastSpace).trim() : common.trim();
    
    if (filtro.length >= 3 && !filtros.includes(filtro)) {
      setFiltros(p => [...p, filtro]);
    } else if (!filtros.includes(descs[0])) {
      // Fallback: usar a primeira descrição
      setFiltros(p => [...p, descs[0]]);
    }
  };

  // ── Filtrar linhas ────────────────────────────────────
  const filtradas = useMemo(() => {
    let result = linhas;

    // Filtro por tipo
    if (tipoFiltro !== "todos") {
      result = result.filter(l => l.tipo === tipoFiltro);
    }

    // Filtro por palavras-chave (OR entre filtros, AND com tipo)
    // Compara tanto com a descrição original quanto com a versão normalizada
    if (filtros.length > 0) {
      result = result.filter(l =>
        filtros.some(f => descricaoBateComFiltro(l.descricao, f))
      );
    }

    return result;
  }, [linhas, filtros, tipoFiltro]);

  // Persistir dados filtrados no localStorage para os Apêndices importarem
  useEffect(() => {
    if (filtradas.length > 0) {
      localStorage.setItem(LS_KEY_DADOS_FILTRADOS, JSON.stringify(filtradas));
    }
  }, [filtradas]);

  // ── Totais ────────────────────────────────────────────
  const totalDebito  = filtradas.filter(l => l.tipo === "debito").reduce((s, l) => s + l.debito, 0);
  const totalCredito = filtradas.filter(l => l.tipo === "credito").reduce((s, l) => s + l.credito, 0);
  const totalGeral   = linhas.filter(l => l.tipo === "debito").reduce((s, l) => s + l.debito, 0);

  // ── Exportar CSV ──────────────────────────────────────
  const exportCSV = () => {
    const header = hasCompetencia 
      ? "Competência,Data,Descrição,Débito (R$),Crédito (R$),Tipo"
      : "Data,Descrição,Débito (R$),Crédito (R$),Tipo";
    const rows = filtradas.map(l =>
      hasCompetencia
        ? `"${l.competencia || ""}","${l.data}","${l.descricao.replace(/"/g, '""')}","${l.debito > 0 ? brl(l.debito) : ""}","${l.credito > 0 ? brl(l.credito) : ""}","${l.tipo}"`
        : `"${l.data}","${l.descricao.replace(/"/g, '""')}","${l.debito > 0 ? brl(l.debito) : ""}","${l.credito > 0 ? brl(l.credito) : ""}","${l.tipo}"`
    );
    const csv = "\uFEFF" + [header, ...rows].join("\n"); // BOM para Excel reconhecer UTF-8
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `extrato-${fileName.replace(".pdf", "")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Exportar XLSX ─────────────────────────────────────
  const exportXLSX = () => {
    const wsData = hasCompetencia
      ? [
          ["Competência", "Data", "Descrição", "Débito (R$)", "Crédito (R$)", "Tipo"],
          ...filtradas.map(l => [
            l.competencia || "",
            l.data,
            l.descricao,
            l.debito > 0 ? l.debito : "",
            l.credito > 0 ? l.credito : "",
            l.tipo === "debito" ? "Débito" : "Crédito",
          ]),
          [],
          ["", "", "TOTAL DÉBITOS", totalDebito, "", ""],
          ["", "", "TOTAL CRÉDITOS", "", totalCredito, ""],
        ]
      : [
          ["Data", "Descrição", "Débito (R$)", "Crédito (R$)", "Tipo"],
          ...filtradas.map(l => [
            l.data,
            l.descricao,
            l.debito > 0 ? l.debito : "",
            l.credito > 0 ? l.credito : "",
            l.tipo === "debito" ? "Débito" : "Crédito",
          ]),
          [],
          ["", "TOTAL DÉBITOS", totalDebito, "", ""],
          ["", "TOTAL CRÉDITOS", "", totalCredito, ""],
        ];

    const ws = XLSX.utils.aoa_to_sheet(wsData);

    // Largura das colunas
    ws["!cols"] = hasCompetencia
      ? [{ wch: 14 }, { wch: 12 }, { wch: 45 }, { wch: 15 }, { wch: 15 }, { wch: 10 }]
      : [{ wch: 12 }, { wch: 45 }, { wch: 15 }, { wch: 15 }, { wch: 10 }];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Extrato");

    // Aba de resumo por filtro
    if (filtros.length > 0) {
      const resumoData = [
        ["Filtro", "Ocorrências", "Total Débito (R$)"],
        ...filtros.map(f => {
          const matches = linhas.filter(l =>
            l.tipo === "debito" && descricaoBateComFiltro(l.descricao, f)
          );
          return [f, matches.length, matches.reduce((s, l) => s + l.debito, 0)];
        }),
      ];
      const wsResumo = XLSX.utils.aoa_to_sheet(resumoData);
      wsResumo["!cols"] = [{ wch: 30 }, { wch: 15 }, { wch: 20 }];
      XLSX.utils.book_append_sheet(wb, wsResumo, "Resumo por Filtro");
    }

    XLSX.writeFile(wb, `extrato-${fileName.replace(".pdf", "")}.xlsx`);
  };

  // ── Exportar PDF ──────────────────────────────────────
  const exportPDF = () => {
    // Criar conteúdo HTML para impressão
    const printContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Extrato - ${fileName}</title>
        <style>
          body { font-family: Arial, sans-serif; font-size: 10px; margin: 20px; }
          h1 { font-size: 14px; margin-bottom: 5px; }
          h2 { font-size: 12px; color: #666; margin-bottom: 15px; }
          table { width: 100%; border-collapse: collapse; margin-top: 10px; }
          th, td { border: 1px solid #ddd; padding: 6px; text-align: left; }
          th { background: #f5f5f5; font-weight: bold; }
          .right { text-align: right; }
          .debito { color: #c00; }
          .credito { color: #080; }
          .total { font-weight: bold; background: #f9f9f9; }
          .info { margin-bottom: 15px; }
          .info span { margin-right: 20px; }
          @media print { body { margin: 0; } }
        </style>
      </head>
      <body>
        <h1>EXTRATO FINANCEIRO</h1>
        <h2>${fileName}</h2>
        <div class="info">
          ${nome ? `<span><strong>Titular:</strong> ${nome}</span>` : ""}
          ${orgao ? `<span><strong>Órgão:</strong> ${orgao}</span>` : ""}
          ${competencia ? `<span><strong>Período:</strong> ${competencia}</span>` : ""}
        </div>
        ${filtros.length > 0 ? `<p><strong>Filtros aplicados:</strong> ${filtros.join(", ")}</p>` : ""}
        <table>
          <thead>
            <tr>
              ${hasCompetencia ? `<th>Competência</th>` : ""}
              <th>Data</th>
              <th>Descrição</th>
              <th class="right">Débito (R$)</th>
              <th class="right">Crédito (R$)</th>
            </tr>
          </thead>
          <tbody>
            ${filtradas.map(l => `
              <tr>
                ${hasCompetencia ? `<td>${l.competencia || ""}</td>` : ""}
                <td>${l.data}</td>
                <td>${l.descricao}</td>
                <td class="right debito">${l.debito > 0 ? brl(l.debito) : ""}</td>
                <td class="right credito">${l.credito > 0 ? brl(l.credito) : ""}</td>
              </tr>
            `).join("")}
          </tbody>
          <tfoot>
            <tr class="total">
              <td colspan="${hasCompetencia ? 3 : 2}">TOTAL (${filtradas.length} registros)</td>
              <td class="right debito">${brl(totalDebito)}</td>
              <td class="right credito">${brl(totalCredito)}</td>
            </tr>
          </tfoot>
        </table>
        <script>window.onload = () => { window.print(); window.close(); }</script>
      </body>
      </html>
    `;
    
    const printWindow = window.open("", "_blank");
    if (printWindow) {
      printWindow.document.write(printContent);
      printWindow.document.close();
    }
  };

  return (
    <div className="space-y-5">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => nav(-1)} className="p-2">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h2 className="text-lg font-bold text-white">Extrato Bancário</h2>
            <p className="text-xs text-[var(--muted)] font-mono">{fileName}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {onReprocess && (
            <Button variant="secondary" onClick={onReprocess} disabled={reprocessing}>
              <RefreshCw className={`w-4 h-4 ${reprocessing ? "animate-spin" : ""}`} /> Reprocessar
            </Button>
          )}
          <Button variant="secondary" onClick={exportCSV}>
            <FileText className="w-4 h-4" /> CSV
          </Button>
          <Button variant="secondary" onClick={exportXLSX}>
            <FileSpreadsheet className="w-4 h-4" /> XLSX
          </Button>
          <Button variant="secondary" onClick={exportPDF}>
            <FileDown className="w-4 h-4" /> PDF
          </Button>
          {onExportToApendice && filtradas.length > 0 && (
            <>
              <Button 
                variant="primary" 
                onClick={() => onExportToApendice(filtradas, "apendice1")}
                className="bg-purple-600 hover:bg-purple-700"
              >
                <Calculator className="w-4 h-4" /> Apêndice 01
              </Button>
              <Button 
                variant="primary" 
                onClick={() => onExportToApendice(filtradas, "apendice2")}
                className="bg-orange-600 hover:bg-orange-700"
              >
                <Calculator className="w-4 h-4" /> Apêndice 02
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Info do titular */}
      {(nome || orgao || competencia) && (
        <Card>
          <CardBody>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              {nome && <div><p className="text-xs text-[var(--muted)] mb-0.5">Titular</p><p className="text-white font-medium">{nome}</p></div>}
              {orgao && <div><p className="text-xs text-[var(--muted)] mb-0.5">Agência / Conta</p><p className="text-white font-medium">{orgao}</p></div>}
              {competencia && <div><p className="text-xs text-[var(--muted)] mb-0.5">Período</p><p className="text-white font-medium">{competencia}</p></div>}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Cards de totais */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Registros", value: String(filtradas.length), icon: Search, color: "text-blue-400" },
          { label: "Total Débitos", value: `R$ ${brl(totalDebito)}`, icon: TrendingDown, color: "text-red-400" },
          { label: "Total Créditos", value: `R$ ${brl(totalCredito)}`, icon: TrendingUp, color: "text-green-400" },
          { label: "Débito Total Geral", value: `R$ ${brl(totalGeral)}`, icon: TrendingDown, color: "text-orange-400" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="surface rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Icon className={`w-4 h-4 ${color}`} />
              <span className="text-xs text-[var(--muted)]">{label}</span>
            </div>
            <p className={`text-lg font-bold font-mono ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Filtros dinâmicos */}
      <Card>
        <CardHeader>
          <Search className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-semibold text-white">Filtros Dinâmicos</span>
          <span className="ml-auto text-xs text-[var(--muted)]">
            {filtradas.length} de {linhas.length} registros
          </span>
        </CardHeader>
        <CardBody className="space-y-4">
          {/* Input de filtro + Dropdown de tipos */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted)]" />
              <input
                value={inputFiltro}
                onChange={e => setInputFiltro(e.target.value)}
                onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addFiltro())}
                placeholder="Buscar por descrição... (ex: PARCELA, SEGURO, INSS)"
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder:text-[var(--muted)] focus:outline-none focus:border-blue-500"
              />
            </div>
            <Button variant="secondary" onClick={() => addFiltro()} disabled={!inputFiltro.trim()}>
              <Plus className="w-4 h-4" /> Adicionar
            </Button>
            
            {/* Dropdown de tipos de lançamentos com checkboxes */}
            <div className="relative">
              <Button 
                variant="secondary" 
                onClick={() => { setDropdownOpen(!dropdownOpen); if (dropdownOpen) setSelectedTipos(new Set()); }}
                className="whitespace-nowrap"
              >
                <List className="w-4 h-4" /> 
                Tipos de Lançamento
                {selectedTipos.size > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 rounded-full bg-blue-500 text-white text-[10px] font-bold">
                    {selectedTipos.size}
                  </span>
                )}
                <ChevronDown className={`w-4 h-4 transition-transform ${dropdownOpen ? "rotate-180" : ""}`} />
              </Button>
              
              {dropdownOpen && (
                <>
                  {/* Overlay para fechar ao clicar fora */}
                  <div 
                    className="fixed inset-0 z-10" 
                    onClick={() => { setDropdownOpen(false); setSelectedTipos(new Set()); }}
                  />
                  
                  {/* Menu dropdown */}
                  <div className="absolute right-0 top-full mt-2 w-[28rem] max-h-96 flex flex-col bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-xl z-20">
                    {/* Header com ações */}
                    <div className="p-3 border-b border-[var(--border)] sticky top-0 bg-[var(--surface)] rounded-t-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-[var(--muted)]">
                          {tiposLancamentos.length} tipos encontrados
                        </p>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => {
                              const available = tiposLancamentos.filter(t => !t.descricoes.some(d => filtros.some(f => d.toLowerCase().includes(f))));
                              if (selectedTipos.size === available.length) {
                                setSelectedTipos(new Set());
                              } else {
                                setSelectedTipos(new Set(available.map(t => t.nome)));
                              }
                            }}
                            className="text-[10px] text-[var(--muted)] hover:text-white underline"
                          >
                            {selectedTipos.size > 0 ? "Desmarcar todos" : "Selecionar todos"}
                          </button>
                        </div>
                      </div>
                      {selectedTipos.size > 0 && (
                        <Button
                          variant="primary"
                          onClick={() => {
                            selectedTipos.forEach(nome => addFiltroFromTipo(nome));
                            setSelectedTipos(new Set());
                            setDropdownOpen(false);
                          }}
                          className="w-full bg-blue-600 hover:bg-blue-700 text-xs py-1.5"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          Adicionar {selectedTipos.size} selecionado{selectedTipos.size > 1 ? "s" : ""}
                        </Button>
                      )}
                    </div>
                    
                    {/* Lista com checkboxes */}
                    <div className="p-1 overflow-y-auto">
                      {tiposLancamentos.map((tipo, idx) => {
                        const alreadyAdded = tipo.descricoes.some(d => 
                          filtros.some(f => d.toLowerCase().includes(f))
                        );
                        const isChecked = selectedTipos.has(tipo.nome);
                        return (
                          <button
                            key={idx}
                            onClick={() => {
                              if (alreadyAdded) return;
                              setSelectedTipos(prev => {
                                const next = new Set(prev);
                                if (next.has(tipo.nome)) next.delete(tipo.nome);
                                else next.add(tipo.nome);
                                return next;
                              });
                            }}
                            disabled={alreadyAdded}
                            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                              alreadyAdded 
                                ? "bg-blue-500/10 text-blue-400/60 cursor-not-allowed" 
                                : isChecked
                                  ? "bg-blue-500/15 text-white"
                                  : "hover:bg-white/5 text-white"
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              {/* Checkbox */}
                              <div className="shrink-0">
                                {alreadyAdded ? (
                                  <CheckSquare className="w-4 h-4 text-blue-400/50" />
                                ) : isChecked ? (
                                  <CheckSquare className="w-4 h-4 text-blue-400" />
                                ) : (
                                  <Square className="w-4 h-4 text-[var(--muted)]" />
                                )}
                              </div>
                              
                              {/* Nome + stats */}
                              <div className="flex items-center justify-between flex-1 min-w-0">
                                <div className="flex flex-col flex-1 min-w-0 mr-2">
                                  <span className="font-medium truncate">
                                    {tipo.descricoes.length === 1 
                                      ? tipo.descricoes[0].replace(/^\[\d+\]\s*/, "")
                                      : tipo.nome}
                                  </span>
                                  {tipo.descricoes.length > 1 && (
                                    <span className="text-[10px] text-[var(--muted)] truncate">
                                      ex: {tipo.descricoes[0].replace(/^\[\d+\]\s*/, "")}
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-3 text-xs shrink-0">
                                  <span className="text-[var(--muted)]">
                                    {tipo.count}x
                                  </span>
                                  {tipo.totalDebito > 0 && (
                                    <span className="text-red-400 font-mono">
                                      -{brl(tipo.totalDebito)}
                                    </span>
                                  )}
                                  {tipo.totalCredito > 0 && (
                                    <span className="text-green-400 font-mono">
                                      +{brl(tipo.totalCredito)}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            {alreadyAdded && (
                              <span className="text-[10px] text-blue-400/50 ml-7">✓ Já adicionado</span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Tags de filtros ativos */}
          {filtros.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {filtros.map(f => (
                <span key={f} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-medium">
                  <Tag className="w-3 h-3" />
                  {f}
                  <button onClick={() => setFiltros(p => p.filter(x => x !== f))} className="ml-1 hover:text-red-400 transition-colors">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
              <button onClick={() => setFiltros([])} className="text-xs text-[var(--muted)] hover:text-red-400 underline transition-colors">
                Limpar todos
              </button>
            </div>
          )}

          {/* Filtro por tipo */}
          <div className="flex gap-2">
            {(["todos", "debito", "credito"] as const).map(t => (
              <button
                key={t}
                onClick={() => setTipoFiltro(t)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  tipoFiltro === t
                    ? t === "debito" ? "bg-red-500/20 text-red-400 border border-red-500/30"
                      : t === "credito" ? "bg-green-500/20 text-green-400 border border-green-500/30"
                      : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    : "bg-white/5 text-[var(--muted)] border border-[var(--border)] hover:text-white"
                }`}
              >
                {t === "todos" ? "Todos" : t === "debito" ? "Débitos" : "Créditos"}
              </button>
            ))}
          </div>

          {/* Resumo por filtro ativo */}
          {filtros.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {filtros.map(f => {
                const matches = linhas.filter(l =>
                  l.tipo === "debito" && descricaoBateComFiltro(l.descricao, f)
                );
                const total = matches.reduce((s, l) => s + l.debito, 0);
                return (
                  <div key={f} className="flex items-center justify-between p-3 rounded-lg bg-white/3 border border-[var(--border)]">
                    <div>
                      <p className="text-xs text-[var(--muted)]">{f}</p>
                      <p className="text-xs text-white mt-0.5">{matches.length} ocorrência(s)</p>
                    </div>
                    <p className="font-mono text-sm font-bold text-red-400">R$ {brl(total)}</p>
                  </div>
                );
              })}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Tabela de transações */}
      <Card>
        <CardHeader>
          <span className="text-sm font-semibold text-white">
            Transações ({filtradas.length})
          </span>
          <div className="ml-auto flex gap-4 text-xs text-[var(--muted)]">
            <span>Débitos: <span className="text-red-400 font-mono font-semibold">R$ {brl(totalDebito)}</span></span>
            <span>Créditos: <span className="text-green-400 font-mono font-semibold">R$ {brl(totalCredito)}</span></span>
          </div>
        </CardHeader>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-xs text-[var(--muted)] bg-white/2">
                {hasCompetencia && (
                  <th className="text-left px-4 py-3 font-medium w-32">Competência</th>
                )}
                <th className="text-left px-4 py-3 font-medium w-28">Data</th>
                <th className="text-left px-4 py-3 font-medium">Descrição</th>
                <th className="text-right px-4 py-3 font-medium w-32">Débito (R$)</th>
                <th className="text-right px-4 py-3 font-medium w-32">Crédito (R$)</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.length === 0 ? (
                <tr>
                  <td colSpan={hasCompetencia ? 5 : 4} className="text-center py-12 text-[var(--muted)]">
                    Nenhuma transação encontrada com os filtros aplicados.
                  </td>
                </tr>
              ) : (
                filtradas.map((l, i) => {
                  // Destacar linhas que batem com algum filtro
                  const matched = filtros.length > 0 && filtros.some(f => descricaoBateComFiltro(l.descricao, f));
                  return (
                    <tr
                      key={i}
                      className={`border-b border-[var(--border)]/40 transition-colors ${
                        matched ? "bg-blue-500/5 hover:bg-blue-500/10" : "hover:bg-white/2"
                      }`}
                    >
                      {hasCompetencia && (
                        <td className="px-4 py-3 font-mono text-xs text-yellow-400 whitespace-nowrap">
                          {l.competencia || ""}
                        </td>
                      )}
                      <td className="px-4 py-3 font-mono text-xs text-[var(--muted)] whitespace-nowrap">
                        {l.data}
                      </td>
                      <td className="px-4 py-3 text-white">
                        <span className={matched ? "text-blue-300 font-medium" : ""}>
                          {l.descricao}
                        </span>
                        {matched && (
                          <span className="ml-2 inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-400">
                            <Tag className="w-2.5 h-2.5" /> filtrado
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-red-400">
                        {l.debito > 0 ? brl(l.debito) : ""}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-green-400">
                        {l.credito > 0 ? brl(l.credito) : ""}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
            {filtradas.length > 0 && (
              <tfoot>
                <tr className="border-t-2 border-[var(--border)] bg-white/3">
                  <td colSpan={hasCompetencia ? 3 : 2} className="px-4 py-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">
                    Total ({filtradas.length} registros)
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-bold text-red-400">
                    {brl(totalDebito)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-bold text-green-400">
                    {brl(totalCredito)}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </Card>
    </div>
  );
}
