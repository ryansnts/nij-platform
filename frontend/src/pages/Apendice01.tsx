import { useState, useMemo, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import * as XLSX from "xlsx";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  ArrowLeft, FileSpreadsheet, FileDown, Calculator,
  TrendingDown, DollarSign, Calendar, Percent, CheckCircle, Import,
} from "lucide-react";
import { brl } from "@/lib/utils";

// ── Chaves do localStorage ──────────────────────────────
const LS_KEY_PARAMS = "nij_apendice01_params";
const LS_KEY_DADOS = "nij_apendice01_dados_importados";
const LS_KEY_EXTRATO_FILTRADOS = "nij_extrato_dados_filtrados";
const LS_KEY_SALDO = "nij_apendice01_saldo_devedor"; // Compartilhado com Apêndice 02
const LS_KEY_ULTIMA_LINHA = "nij_apendice01_ultima_linha"; // Data + saldo da última linha

interface DadosEntrada {
  data: string;
  descricao: string;
  debito: number;
  credito: number;
  tipo: "debito" | "credito";
}

interface LinhaCalculo {
  qtde: number | string;
  dataVencimento: string;
  valorPago: number;
  jurosDevidos: number;
  amortizacao: number;
  saqueConvEmprestimo: number;
  saldoDevedor: number;
}

interface Apendice01Params {
  requerente: string;
  requerido: string;
  valorSaque: number;
  valorSaqueComp: number;
  valorFinanciado: number;
  dataSaque: string;
  qtdePrestacoes: number;
  taxaMedia: number;
  primeiroVencimento: string;
  prestacaoPaga: number;
}

const defaultParams: Apendice01Params = {
  requerente: "MARCIA LIMA DE OLIVEIRA GADELHA",
  requerido: "BANCO OLÉ BONSUCESSO",
  valorSaque: 2249.77,
  valorSaqueComp: 0,
  valorFinanciado: 2368.37,
  dataSaque: "21/01/2012",
  qtdePrestacoes: 23,
  taxaMedia: 1.97,
  primeiroVencimento: "09/04/2012",
  prestacaoPaga: 77.46,
};

function loadParams(): Apendice01Params {
  try {
    const raw = localStorage.getItem(LS_KEY_PARAMS);
    if (raw) return { ...defaultParams, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return defaultParams;
}

function loadDadosImportados(): DadosEntrada[] | null {
  try {
    const raw = localStorage.getItem(LS_KEY_DADOS);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
}

export default function Apendice01() {
  const nav = useNavigate();
  const location = useLocation();
  const dadosNavegacao = location.state?.dados as DadosEntrada[] | undefined;

  // Se veio dados pela navegação, usa eles. Senão, tenta localStorage.
  const dadosImportados = dadosNavegacao || loadDadosImportados();
  const temDadosImportados = dadosImportados && dadosImportados.length > 0;

  // Persistir dados importados quando vêm pela navegação
  useEffect(() => {
    if (dadosNavegacao && dadosNavegacao.length > 0) {
      localStorage.setItem(LS_KEY_DADOS, JSON.stringify(dadosNavegacao));
    }
  }, [dadosNavegacao]);

  // Dados do cabeçalho - carregados do localStorage
  const saved = loadParams();
  const [requerente, setRequerente] = useState(saved.requerente);
  const [requerido, setRequerido] = useState(saved.requerido);
  const [valorSaque, setValorSaque] = useState(saved.valorSaque);
  const [valorSaqueComp, setValorSaqueComp] = useState(saved.valorSaqueComp);
  const [jurosSaque, setJurosSaque] = useState(118.60);
  const [valorFinanciado, setValorFinanciado] = useState(saved.valorFinanciado);
  const [dataSaque, setDataSaque] = useState(saved.dataSaque);
  const [qtdePrestacoes, setQtdePrestacoes] = useState(saved.qtdePrestacoes);
  const [taxaMedia, setTaxaMedia] = useState(saved.taxaMedia);
  const [primeiroVencimento, setPrimeiroVencimento] = useState(saved.primeiroVencimento);
  const [prestacaoPaga, setPrestacaoPaga] = useState(saved.prestacaoPaga);

  // Linhas de cálculo
  const [linhas, setLinhas] = useState<LinhaCalculo[]>([]);

  // ── Persistir parâmetros no localStorage ──────────────
  useEffect(() => {
    const params: Apendice01Params = {
      requerente, requerido, valorSaque, valorSaqueComp,
      valorFinanciado, dataSaque, qtdePrestacoes, taxaMedia,
      primeiroVencimento, prestacaoPaga,
    };
    localStorage.setItem(LS_KEY_PARAMS, JSON.stringify(params));
  }, [requerente, requerido, valorSaque, valorSaqueComp, valorFinanciado, dataSaque, qtdePrestacoes, taxaMedia, primeiroVencimento, prestacaoPaga]);

  // ── Persistir saldo devedor e data da última linha para o Apêndice 02 ──
  useEffect(() => {
    if (linhas.length > 0) {
      const ultimaLinha = linhas[linhas.length - 1];
      const qtdePrestacao = linhas.filter(l => typeof l.qtde === "number").length;
      localStorage.setItem(LS_KEY_SALDO, JSON.stringify(ultimaLinha.saldoDevedor));
      // Salvar dados da última linha + qtde prestações para o Apêndice 02
      localStorage.setItem(LS_KEY_ULTIMA_LINHA, JSON.stringify({
        data: ultimaLinha.dataVencimento,
        saldoDevedor: ultimaLinha.saldoDevedor,
        qtdePrestacoes: qtdePrestacao,
      }));
    }
  }, [linhas]);

  // Função para calcular diferença em dias entre duas datas
  const calcularDiasEntreDatas = (dataInicio: string, dataFim: string): number => {
    const parseData = (dataStr: string): Date => {
      const [dia, mes, ano] = dataStr.split("/").map(Number);
      return new Date(ano, mes - 1, dia);
    };
    const inicio = parseData(dataInicio);
    const fim = parseData(dataFim);
    const diffTime = fim.getTime() - inicio.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  // Calcular Juros do Saque automaticamente
  useEffect(() => {
    const diasEntreDatas = calcularDiasEntreDatas(dataSaque, primeiroVencimento);
    const taxaMensal = taxaMedia / 100;
    const jurosCalculado = valorSaque * (taxaMensal / 30) * diasEntreDatas;
    setJurosSaque(Number(jurosCalculado.toFixed(2)));
  }, [valorSaque, taxaMedia, dataSaque, primeiroVencimento]);

  // Inicializar linhas baseado nos dados importados ou criar padrão
  useEffect(() => {
    if (temDadosImportados) {
      const novasLinhas: LinhaCalculo[] = dadosImportados!
        .filter(d => d.tipo === "debito" && d.debito > 0)
        .map((d, idx) => ({
          qtde: idx + 1,
          dataVencimento: d.data,
          valorPago: d.debito,
          jurosDevidos: 0,
          amortizacao: 0,
          saqueConvEmprestimo: 0,
          saldoDevedor: 0,
        }));
      
      if (novasLinhas.length > 0) {
        setLinhas(novasLinhas);
        setQtdePrestacoes(novasLinhas.length);
        setPrestacaoPaga(novasLinhas[0]?.valorPago || 0);
      }
    } else {
      gerarLinhasPadrao();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const gerarLinhasPadrao = useCallback(() => {
    const novasLinhas: LinhaCalculo[] = [];
    const taxaMensal = taxaMedia / 100;
    
    const diasEntreDatas = calcularDiasEntreDatas(dataSaque, primeiroVencimento);
    const jurosDoSaqueCalculado = valorSaque * (taxaMensal / 30) * diasEntreDatas;
    
    // Linha SQ01
    novasLinhas.push({
      qtde: "SQ01",
      dataVencimento: dataSaque,
      valorPago: 0,
      jurosDevidos: 0,
      amortizacao: 0,
      saqueConvEmprestimo: valorSaque,
      saldoDevedor: valorSaque,
    });

    let saldoAtual = valorSaque;
    
    for (let i = 1; i <= qtdePrestacoes; i++) {
      let juros: number;
      
      if (i === 1) {
        juros = jurosDoSaqueCalculado;
      } else {
        juros = saldoAtual * taxaMensal;
      }
      
      const amortizacao = prestacaoPaga - juros;
      saldoAtual = saldoAtual - amortizacao;
      
      novasLinhas.push({
        qtde: i,
        dataVencimento: calcularDataVencimento(primeiroVencimento, i - 1),
        valorPago: prestacaoPaga,
        jurosDevidos: Math.max(0, juros),
        amortizacao: Math.max(0, amortizacao),
        saqueConvEmprestimo: 0,
        saldoDevedor: Math.max(0, saldoAtual),
      });
    }

    setLinhas(novasLinhas);
  }, [valorSaque, taxaMedia, dataSaque, primeiroVencimento, qtdePrestacoes, prestacaoPaga]);

  const calcularDataVencimento = (dataInicial: string, mesesAdicionar: number): string => {
    const [dia, mes, ano] = dataInicial.split("/").map(Number);
    const data = new Date(ano, mes - 1 + mesesAdicionar, dia);
    return data.toLocaleDateString("pt-BR");
  };

  const recalcular = () => {
    gerarLinhasPadrao();
  };

  // Limpar dados importados e voltar ao modo manual
  const limparImportacao = () => {
    localStorage.removeItem(LS_KEY_DADOS);
    gerarLinhasPadrao();
  };

  // Importar dados filtrados do Extrato (via localStorage)
  const importarDoExtrato = () => {
    try {
      const raw = localStorage.getItem(LS_KEY_EXTRATO_FILTRADOS);
      if (!raw) {
        alert("Nenhum dado filtrado encontrado. Abra o Extrato, aplique os filtros desejados e volte aqui.");
        return;
      }
      const dados: DadosEntrada[] = JSON.parse(raw);
      const debitos = dados.filter(d => d.tipo === "debito" && d.debito > 0);
      if (debitos.length === 0) {
        alert("Nenhum débito encontrado nos dados filtrados do Extrato.");
        return;
      }
      // Salvar como dados importados
      localStorage.setItem(LS_KEY_DADOS, JSON.stringify(dados));
      // Gerar linhas
      const novasLinhas: LinhaCalculo[] = debitos.map((d, idx) => ({
        qtde: idx + 1,
        dataVencimento: d.data,
        valorPago: d.debito,
        jurosDevidos: 0,
        amortizacao: 0,
        saqueConvEmprestimo: 0,
        saldoDevedor: 0,
      }));
      setLinhas(novasLinhas);
      setQtdePrestacoes(novasLinhas.length);
      setPrestacaoPaga(novasLinhas[0]?.valorPago || 0);
    } catch {
      alert("Erro ao importar dados do Extrato.");
    }
  };

  // Totais - excluindo a linha SQ01
  const totais = useMemo(() => {
    const linhasPrestacao = linhas.filter(l => typeof l.qtde === "number");
    const totalPago = linhasPrestacao.reduce((s, l) => s + (typeof l.valorPago === "number" ? l.valorPago : 0), 0);
    const totalJuros = linhasPrestacao.reduce((s, l) => s + l.jurosDevidos, 0);
    const totalAmortizacao = linhasPrestacao.reduce((s, l) => s + l.amortizacao, 0);
    return { totalPago, totalJuros, totalAmortizacao };
  }, [linhas]);

  // Exportar XLSX
  const exportXLSX = () => {
    const wsData = [
      ["PERÍCIA ESPECIALIZADA"],
      ["APÊNDICE 01: CONVERSÃO DO 1º SAQUE PARA EMPRÉSTIMO CONSIGNADO"],
      [],
      [`Requerente: ${requerente}`],
      [`Requerido: ${requerido}`],
      [],
      ["Valor do 1º Saque", valorSaque, "", "Qtde Prestações", qtdePrestacoes],
      ["Valor do Saque Comp.", valorSaqueComp, "", "Taxa MÉDIA (a.m.)", `${taxaMedia}%`],
      ["Juros do Saque", jurosSaque, "", "1º Vencimento", primeiroVencimento],
      ["Valor Financiado", valorFinanciado, "", "Prestação Paga", prestacaoPaga],
      ["Data do 1º Saque", dataSaque],
      [],
      ["Qtde", "Data Vencimento", "Valor Pago = Prestação Devida", "Juros Devidos - Taxa Média", "Amortização", "Saque Conv. Para Empréstimo", "Saldo Devedor"],
      ...linhas.map(l => {
        const isLinhaSaque = typeof l.qtde === "string";
        return [
          l.qtde,
          l.dataVencimento,
          l.valorPago > 0 ? l.valorPago.toFixed(2) : "",
          !isLinhaSaque && l.jurosDevidos > 0 ? l.jurosDevidos.toFixed(2) : "",
          !isLinhaSaque && l.amortizacao > 0 ? l.amortizacao.toFixed(2) : "",
          l.saqueConvEmprestimo > 0 ? l.saqueConvEmprestimo.toFixed(2) : "",
          l.saldoDevedor.toFixed(2),
        ];
      }),
      [],
      ["TOTAIS", "", totais.totalPago.toFixed(2), totais.totalJuros.toFixed(2), totais.totalAmortizacao.toFixed(2), "", ""],
    ];

    const ws = XLSX.utils.aoa_to_sheet(wsData);
    ws["!cols"] = [
      { wch: 8 }, { wch: 14 }, { wch: 18 }, { wch: 18 }, { wch: 14 }, { wch: 18 }, { wch: 14 },
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Apêndice 01");
    XLSX.writeFile(wb, `apendice01-conversao-saque.xlsx`);
  };

  // Exportar PDF
  const exportPDF = () => {
    const printContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Apêndice 01 - Conversão do 1º Saque</title>
        <style>
          body { font-family: Arial, sans-serif; font-size: 9px; margin: 15px; }
          h1 { font-size: 11px; text-align: center; margin-bottom: 3px; color: #666; }
          h2 { font-size: 12px; text-align: center; margin-bottom: 15px; color: #000; }
          .header { display: flex; justify-content: space-between; margin-bottom: 15px; }
          .header-col { width: 48%; }
          .header-row { display: flex; justify-content: space-between; margin-bottom: 3px; }
          .header-row span:first-child { font-weight: bold; }
          table { width: 100%; border-collapse: collapse; font-size: 8px; }
          th, td { border: 1px solid #000; padding: 4px; text-align: center; }
          th { background: #e0e0e0; font-weight: bold; }
          .right { text-align: right; }
          .total { font-weight: bold; background: #f0f0f0; }
          .saque-row { background: #fffde7; }
          @media print { body { margin: 5mm; } }
        </style>
      </head>
      <body>
        <h1>PERÍCIA ESPECIALIZADA</h1>
        <h2>APÊNDICE 01: CONVERSÃO DO 1º SAQUE PARA EMPRÉSTIMO CONSIGNADO</h2>
        <p><strong>Requerente:</strong> ${requerente}</p>
        <p><strong>Requerido:</strong> ${requerido}</p>
        <div class="header">
          <div class="header-col">
            <div class="header-row"><span>Valor do 1º Saque</span><span>${brl(valorSaque)}</span></div>
            <div class="header-row"><span>Valor do Saque Comp.</span><span>${brl(valorSaqueComp)}</span></div>
            <div class="header-row"><span>Juros do Saque</span><span>${brl(jurosSaque)}</span></div>
            <div class="header-row"><span>Valor Financiado</span><span>${brl(valorFinanciado)}</span></div>
            <div class="header-row"><span>Data do 1º Saque</span><span>${dataSaque}</span></div>
          </div>
          <div class="header-col">
            <div class="header-row"><span>Qtde Prestações</span><span>${qtdePrestacoes}</span></div>
            <div class="header-row"><span>Taxa MÉDIA (a.m.)</span><span>${taxaMedia}%</span></div>
            <div class="header-row"><span>1º Vencimento</span><span>${primeiroVencimento}</span></div>
            <div class="header-row"><span>Prestação Paga</span><span>${brl(prestacaoPaga)}</span></div>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Qtde</th><th>Data Vencimento</th><th>Valor Pago = Prestação Devida</th>
              <th>Juros Devidos - Taxa Média</th><th>Amortização</th>
              <th>Saque Conv. Para Empréstimo</th><th>Saldo Devedor</th>
            </tr>
          </thead>
          <tbody>
            ${linhas.map(l => {
              const isLinhaSaque = typeof l.qtde === "string";
              return `
              <tr class="${isLinhaSaque ? 'saque-row' : ''}">
                <td><strong>${l.qtde}</strong></td>
                <td>${l.dataVencimento}</td>
                <td class="right">${l.valorPago > 0 ? brl(l.valorPago) : ""}</td>
                <td class="right">${!isLinhaSaque && l.jurosDevidos > 0 ? brl(l.jurosDevidos) : ""}</td>
                <td class="right">${!isLinhaSaque && l.amortizacao > 0 ? brl(l.amortizacao) : ""}</td>
                <td class="right"><strong>${l.saqueConvEmprestimo > 0 ? brl(l.saqueConvEmprestimo) : ""}</strong></td>
                <td class="right">${brl(l.saldoDevedor)}</td>
              </tr>
            `}).join("")}
          </tbody>
          <tfoot>
            <tr class="total">
              <td colspan="2">TOTAIS</td>
              <td class="right">${brl(totais.totalPago)}</td>
              <td class="right">${brl(totais.totalJuros)}</td>
              <td class="right">${brl(totais.totalAmortizacao)}</td>
              <td></td><td></td>
            </tr>
          </tfoot>
        </table>
        <script>window.onload = () => { window.print(); window.close(); }</script>
      </body>
      </html>
    `;
    const printWindow = window.open("", "_blank");
    if (printWindow) { printWindow.document.write(printContent); printWindow.document.close(); }
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
            <h2 className="text-lg font-bold text-white">Apêndice 01</h2>
            <p className="text-xs text-[var(--muted)]">Conversão do 1º Saque para Empréstimo Consignado</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="primary" onClick={importarDoExtrato} className="bg-cyan-600 hover:bg-cyan-700">
            <Import className="w-4 h-4" /> Importar do Extrato
          </Button>
          <Button variant="secondary" onClick={recalcular}>
            <Calculator className="w-4 h-4" /> Recalcular
          </Button>
          <Button variant="secondary" onClick={exportXLSX}>
            <FileSpreadsheet className="w-4 h-4" /> XLSX
          </Button>
          <Button variant="secondary" onClick={exportPDF}>
            <FileDown className="w-4 h-4" /> PDF
          </Button>
        </div>
      </div>

      {/* Indicador de dados importados */}
      {temDadosImportados && (
        <Card>
          <CardBody>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <div>
                  <p className="text-sm font-medium text-white">Dados Importados do Extrato</p>
                  <p className="text-xs text-[var(--muted)]">
                    {linhas.filter(l => typeof l.qtde === "number").length} prestações com datas e valores reais
                  </p>
                </div>
              </div>
              <Button 
                variant="ghost" 
                onClick={limparImportacao}
                className="text-xs text-red-400 hover:text-red-300"
              >
                Limpar importação
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Dados do Cabeçalho */}
      <Card>
        <CardHeader>
          <span className="text-sm font-semibold text-white">Dados do Contrato</span>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <Input label="Requerente" value={requerente} onChange={e => setRequerente(e.target.value)} />
              <Input label="Requerido" value={requerido} onChange={e => setRequerido(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input label="Valor do 1º Saque" type="number" step="0.01" value={valorSaque} onChange={e => setValorSaque(Number(e.target.value))} />
              <Input label="Qtde Prestações" type="number" value={qtdePrestacoes} onChange={e => setQtdePrestacoes(Number(e.target.value))} />
              <Input label="Juros do Saque" type="number" step="0.01" value={jurosSaque} readOnly className="bg-gray-800/50" />
              <Input label="Taxa Média (% a.m.)" type="number" step="0.01" value={taxaMedia} onChange={e => setTaxaMedia(Number(e.target.value))} />
              <Input label="Valor Financiado" type="number" step="0.01" value={valorFinanciado} onChange={e => setValorFinanciado(Number(e.target.value))} />
              <Input label="1º Vencimento" value={primeiroVencimento} onChange={e => setPrimeiroVencimento(e.target.value)} />
              <Input label="Data do 1º Saque" value={dataSaque} onChange={e => setDataSaque(e.target.value)} />
              <Input label="Prestação Paga" type="number" step="0.01" value={prestacaoPaga} onChange={e => setPrestacaoPaga(Number(e.target.value))} />
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Pago", value: `R$ ${brl(totais.totalPago)}`, icon: DollarSign, color: "text-blue-400" },
          { label: "Total Juros", value: `R$ ${brl(totais.totalJuros)}`, icon: Percent, color: "text-red-400" },
          { label: "Total Amortização", value: `R$ ${brl(totais.totalAmortizacao)}`, icon: TrendingDown, color: "text-green-400" },
          { label: "Prestações", value: String(linhas.length), icon: Calendar, color: "text-purple-400" },
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

      {/* Tabela de Cálculo */}
      <Card>
        <CardHeader>
          <span className="text-sm font-semibold text-white">Demonstrativo de Cálculo</span>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-xs text-[var(--muted)] bg-white/2">
                <th className="text-center px-3 py-3 font-medium w-16">Qtde</th>
                <th className="text-center px-3 py-3 font-medium w-28">Data Vencimento</th>
                <th className="text-right px-3 py-3 font-medium">Valor Pago</th>
                <th className="text-right px-3 py-3 font-medium">Juros Devidos</th>
                <th className="text-right px-3 py-3 font-medium">Amortização</th>
                <th className="text-right px-3 py-3 font-medium">Saque Conv.</th>
                <th className="text-right px-3 py-3 font-medium">Saldo Devedor</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((l, i) => {
                const isLinhaSaque = typeof l.qtde === "string";
                return (
                  <tr key={i} className={`border-b border-[var(--border)]/40 hover:bg-white/2 ${isLinhaSaque ? "bg-yellow-500/5" : ""}`}>
                    <td className="px-3 py-2 text-center font-mono text-xs font-semibold">{l.qtde}</td>
                    <td className="px-3 py-2 text-center font-mono text-xs">{l.dataVencimento}</td>
                    <td className="px-3 py-2 text-right font-mono text-blue-400">
                      {l.valorPago > 0 ? brl(l.valorPago) : ""}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-red-400">
                      {!isLinhaSaque && l.jurosDevidos > 0 ? brl(l.jurosDevidos) : ""}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-green-400">
                      {!isLinhaSaque && l.amortizacao > 0 ? brl(l.amortizacao) : ""}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-purple-400 font-semibold">
                      {l.saqueConvEmprestimo > 0 ? brl(l.saqueConvEmprestimo) : ""}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-orange-400">{brl(l.saldoDevedor)}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-[var(--border)] bg-white/3">
                <td colSpan={2} className="px-3 py-3 text-xs font-semibold text-[var(--muted)] uppercase">Totais</td>
                <td className="px-3 py-3 text-right font-mono font-bold text-blue-400">{brl(totais.totalPago)}</td>
                <td className="px-3 py-3 text-right font-mono font-bold text-red-400">{brl(totais.totalJuros)}</td>
                <td className="px-3 py-3 text-right font-mono font-bold text-green-400">{brl(totais.totalAmortizacao)}</td>
                <td className="px-3 py-3"></td>
                <td className="px-3 py-3"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>
    </div>
  );
}
