import { useState, useMemo, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import * as XLSX from "xlsx";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import {
  ArrowLeft, FileSpreadsheet, FileDown, Calculator,
  TrendingUp, DollarSign, Scale, RefreshCw, Database,
  CheckCircle, AlertCircle, Wifi, Import,
} from "lucide-react";
import { brl } from "@/lib/utils";
import { bcb } from "@/lib/api";

// ── Chaves do localStorage ──────────────────────────────
const LS_KEY_PARAMS = "nij_apendice02_params";
const LS_KEY_DADOS = "nij_apendice02_dados_importados";
const LS_KEY_SALDO_AP01 = "nij_apendice01_saldo_devedor";
const LS_KEY_ULTIMA_LINHA_AP01 = "nij_apendice01_ultima_linha";
const LS_KEY_EXTRATO_FILTRADOS = "nij_extrato_dados_filtrados";

interface DadosEntrada {
  data: string;
  descricao: string;
  debito: number;
  credito: number;
  tipo: "debito" | "credito";
}

interface LinhaCalculo {
  qtde: number;
  dataPagto: string;
  valorPago: number;
  fatorINPC: number;
  valorCorrigido: number;
  dataCitacao: string;
  dataCalculo: string;
  taxaJurosMora: number;
  diasJurosMora: number;
  valorJurosMora: number;
  totalCreditoRestituir: number;
  totalCreditoRestituirDobro: number;
  compras: number;
  fatorCompras: number;
  comprasCorrigidas: number;
  totalDebitoCompensar: number;
}

type StatusINPC = "idle" | "loading" | "success" | "error";

interface Apendice02Params {
  requerente: string;
  requerido: string;
  dataCitacao: string;
  dataCalculo: string;
  taxaJurosMora: number;
  primeiroVencimentoOriginal: string;
  qtdePrestacoesOriginal: number;
  qtdeParcelasIndevidas: number;
  prestacaoPaga: number;
}

const defaultParams: Apendice02Params = {
  requerente: "MARCIA LIMA DE OLIVEIRA GADELHA",
  requerido: "BANCO OLÉ BONSUCESSO",
  dataCitacao: "28/02/2023",
  dataCalculo: new Date().toLocaleDateString("pt-BR"),
  taxaJurosMora: 1.0,
  primeiroVencimentoOriginal: "09/04/2012",
  qtdePrestacoesOriginal: 23,
  qtdeParcelasIndevidas: 80,
  prestacaoPaga: 77.46,
};

function loadParams(): Apendice02Params {
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

function loadSaldoDevedorAp01(): number {
  try {
    const raw = localStorage.getItem(LS_KEY_SALDO_AP01);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return 0;
}

function loadUltimaLinhaAp01(): { data: string; saldoDevedor: number; qtdePrestacoes: number } | null {
  try {
    const raw = localStorage.getItem(LS_KEY_ULTIMA_LINHA_AP01);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
}

function loadDadosFiltradosExtrato(): DadosEntrada[] | null {
  try {
    const raw = localStorage.getItem(LS_KEY_EXTRATO_FILTRADOS);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
}

export default function Apendice02() {
  const nav = useNavigate();
  const location = useLocation();
  const dadosNavegacao = location.state?.dados as DadosEntrada[] | undefined;

  // Se veio dados pela navegação, usa eles. Senão, tenta localStorage.
  const dadosImportados = dadosNavegacao || loadDadosImportados();
  const temDadosImportados = !!(dadosImportados && dadosImportados.length > 0);

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
  const [dataCitacao, setDataCitacao] = useState(saved.dataCitacao);
  const [dataCalculo, setDataCalculo] = useState(saved.dataCalculo);
  const [taxaJurosMora, setTaxaJurosMora] = useState(saved.taxaJurosMora);
  
  const [primeiroVencimentoOriginal, setPrimeiroVencimentoOriginal] = useState(saved.primeiroVencimentoOriginal);
  const [qtdePrestacoesOriginal, setQtdePrestacoesOriginal] = useState(saved.qtdePrestacoesOriginal);
  const [qtdeParcelasIndevidas, setQtdeParcelasIndevidas] = useState(saved.qtdeParcelasIndevidas);
  const [prestacaoPaga, setPrestacaoPaga] = useState(saved.prestacaoPaga);

  // Estado do INPC
  const [statusINPC, setStatusINPC] = useState<StatusINPC>("idle");
  const [fatoresINPC, setFatoresINPC] = useState<Record<string, number>>({});
  const [erroINPC, setErroINPC] = useState<string | null>(null);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<string | null>(null);

  // Linhas de cálculo
  const [linhas, setLinhas] = useState<LinhaCalculo[]>([]);

  // Saldo devedor do Apêndice 01 (para a 1ª linha)
  const saldoDevedorAp01 = loadSaldoDevedorAp01();

  // ── Persistir parâmetros no localStorage ──────────────
  useEffect(() => {
    const params: Apendice02Params = {
      requerente, requerido, dataCitacao, dataCalculo, taxaJurosMora,
      primeiroVencimentoOriginal, qtdePrestacoesOriginal, qtdeParcelasIndevidas, prestacaoPaga,
    };
    localStorage.setItem(LS_KEY_PARAMS, JSON.stringify(params));
  }, [requerente, requerido, dataCitacao, dataCalculo, taxaJurosMora, primeiroVencimentoOriginal, qtdePrestacoesOriginal, qtdeParcelasIndevidas, prestacaoPaga]);

  // Calcular dias entre duas datas
  const calcularDias = useCallback((dataInicio: string, dataFim: string): number => {
    const parseData = (d: string) => {
      const [dia, mes, ano] = d.split("/").map(Number);
      return new Date(ano, mes - 1, dia);
    };
    const inicio = parseData(dataInicio);
    const fim = parseData(dataFim);
    return Math.max(0, Math.floor((fim.getTime() - inicio.getTime()) / (1000 * 60 * 60 * 24)));
  }, []);

  // Calcular data de vencimento
  const calcularDataVencimento = useCallback((dataInicial: string, mesesAdicionar: number): string => {
    const [dia, mes, ano] = dataInicial.split("/").map(Number);
    const data = new Date(ano, mes - 1 + mesesAdicionar, dia);
    return data.toLocaleDateString("pt-BR");
  }, []);

  // Calcular a data da última parcela do contrato original (início do Apêndice 02)
  const calcularDataUltimaParcela = useCallback((): string => {
    return calcularDataVencimento(primeiroVencimentoOriginal, qtdePrestacoesOriginal - 1);
  }, [primeiroVencimentoOriginal, qtdePrestacoesOriginal, calcularDataVencimento]);

  // Buscar fatores INPC do Banco Central
  const buscarFatoresINPC = useCallback(async (datas: string[]) => {
    if (datas.length === 0) return;
    
    setStatusINPC("loading");
    setErroINPC(null);
    
    try {
      const response = await bcb.calcularFatoresINPC(datas, dataCalculo);
      setFatoresINPC(response.data.fatores);
      setStatusINPC("success");
      setUltimaAtualizacao(new Date().toLocaleString("pt-BR"));
    } catch (error: unknown) {
      console.error("Erro ao buscar INPC:", error);
      setStatusINPC("error");
      const errorMessage = error instanceof Error ? error.message : "Erro desconhecido";
      setErroINPC(`Erro ao consultar BCB: ${errorMessage}`);
      const fallback: Record<string, number> = {};
      datas.forEach(d => fallback[d] = 1.0);
      setFatoresINPC(fallback);
    }
  }, [dataCalculo]);

  // Atualizar linhas quando fatores INPC mudam
  useEffect(() => {
    if (Object.keys(fatoresINPC).length === 0) return;
    
    setLinhas(prev => prev.map(l => {
      const fator = fatoresINPC[l.dataPagto] || 1.0;
      const valorCorrigido = l.valorPago * fator;
      const dias = calcularDias(dataCitacao, dataCalculo);
      const jurosMora = valorCorrigido * (taxaJurosMora / 100) * (dias / 30);
      const totalRestituir = valorCorrigido + jurosMora;
      
      return {
        ...l,
        fatorINPC: fator,
        valorCorrigido,
        dataCitacao,
        dataCalculo,
        taxaJurosMora,
        diasJurosMora: dias,
        valorJurosMora: jurosMora,
        totalCreditoRestituir: totalRestituir,
        totalCreditoRestituirDobro: totalRestituir * 2,
      };
    }));
  }, [fatoresINPC, dataCitacao, dataCalculo, taxaJurosMora, calcularDias]);

  // ── Inicializar linhas ────────────────────────────────
  // REGRA: A 1ª linha do Apêndice 02 começa a partir da última linha do Apêndice 01
  //   - Data = data da última parcela do Apêndice 01
  //   - Valor Pago = Saldo Devedor da última linha do Apêndice 01
  // As demais linhas usam os dados importados do Extrato ou geração automática
  useEffect(() => {
    let novasLinhas: LinhaCalculo[];
    const ultimaLinhaAp01 = loadUltimaLinhaAp01();
    const saldo = ultimaLinhaAp01?.saldoDevedor ?? saldoDevedorAp01;
    const dataUltimaAp01 = ultimaLinhaAp01?.data ?? "";
    
    if (temDadosImportados) {
      // DADOS IMPORTADOS DO EXTRATO
      const debitos = dadosImportados!.filter(d => d.tipo === "debito" && d.debito > 0);
      
      novasLinhas = [];
      
      // 1ª LINHA: dados da última parcela do Apêndice 01
      if (saldo > 0 && dataUltimaAp01) {
        novasLinhas.push({
          qtde: 1,
          dataPagto: dataUltimaAp01,  // Data da última parcela do Ap.01
          valorPago: saldo,            // Saldo Devedor do Ap.01
          fatorINPC: 1.0,
          valorCorrigido: saldo,
          dataCitacao,
          dataCalculo,
          taxaJurosMora,
          diasJurosMora: 0,
          valorJurosMora: 0,
          totalCreditoRestituir: saldo,
          totalCreditoRestituirDobro: saldo * 2,
          compras: 0,
          fatorCompras: 1.0,
          comprasCorrigidas: 0,
          totalDebitoCompensar: 0,
        });
      }
      
      // DEMAIS LINHAS: dados do Extrato filtrado
      debitos.forEach((d, idx) => {
        const qtde = saldo > 0 && dataUltimaAp01 ? idx + 2 : idx + 1;
        novasLinhas.push({
          qtde,
          dataPagto: d.data,
          valorPago: d.debito,
          fatorINPC: 1.0,
          valorCorrigido: d.debito,
          dataCitacao,
          dataCalculo,
          taxaJurosMora,
          diasJurosMora: 0,
          valorJurosMora: 0,
          totalCreditoRestituir: d.debito,
          totalCreditoRestituirDobro: d.debito * 2,
          compras: 0,
          fatorCompras: 1.0,
          comprasCorrigidas: 0,
          totalDebitoCompensar: 0,
        });
      });
      
      if (debitos.length > 0) {
        setQtdeParcelasIndevidas(novasLinhas.length);
        const valorMedio = debitos.reduce((s, d) => s + d.debito, 0) / debitos.length;
        setPrestacaoPaga(Number(valorMedio.toFixed(2)));
      }
    } else {
      // GERAÇÃO AUTOMÁTICA
      const dataUltimaParcela = calcularDataUltimaParcela();
      
      novasLinhas = [];
      for (let i = 0; i < qtdeParcelasIndevidas; i++) {
        const dataVenc = calcularDataVencimento(dataUltimaParcela, i);
        // 1ª linha usa o saldo devedor do Apêndice 01
        const valor = i === 0 && saldo > 0 ? saldo : prestacaoPaga;
        novasLinhas.push({
          qtde: i + 1,
          dataPagto: dataVenc,
          valorPago: valor,
          fatorINPC: 1.0,
          valorCorrigido: valor,
          dataCitacao,
          dataCalculo,
          taxaJurosMora,
          diasJurosMora: 0,
          valorJurosMora: 0,
          totalCreditoRestituir: valor,
          totalCreditoRestituirDobro: valor * 2,
          compras: 0,
          fatorCompras: 1.0,
          comprasCorrigidas: 0,
          totalDebitoCompensar: 0,
        });
      }
    }
    
    setLinhas(novasLinhas);
    
    const datas = novasLinhas.map(l => l.dataPagto);
    buscarFatoresINPC(datas);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Helper: criar uma linha de cálculo
  const criarLinha = (qtde: number, data: string, valor: number): LinhaCalculo => ({
    qtde,
    dataPagto: data,
    valorPago: valor,
    fatorINPC: 1.0,
    valorCorrigido: valor,
    dataCitacao,
    dataCalculo,
    taxaJurosMora,
    diasJurosMora: 0,
    valorJurosMora: 0,
    totalCreditoRestituir: valor,
    totalCreditoRestituirDobro: valor * 2,
    compras: 0,
    fatorCompras: 1.0,
    comprasCorrigidas: 0,
    totalDebitoCompensar: 0,
  });

  // ── RECALCULAR: Pega os dados do Extrato, pula as parcelas do Ap.01, usa o restante ──
  // REGRA: Se o Extrato tem 119 débitos e o Ap.01 usou 23, o Ap.02 calcula os 96 restantes
  // A 1ª linha = saldo devedor + data da última linha do Ap.01
  // As datas são SEQUENCIAIS mês a mês a partir da última data do Ap.01
  // Os valores vêm dos débitos restantes do Extrato
  const recalcularComDadosAp01 = useCallback(() => {
    const ultimaAp01 = loadUltimaLinhaAp01();
    const dadosExtrato = loadDadosFiltradosExtrato();
    
    if (!ultimaAp01) {
      alert("Dados do Apêndice 01 não encontrados. Abra o Apêndice 01 e clique em Recalcular primeiro.");
      return;
    }
    
    if (!dadosExtrato || dadosExtrato.length === 0) {
      alert("Nenhum dado filtrado do Extrato encontrado. Abra o Extrato e aplique os filtros primeiro.");
      return;
    }
    
    const todosDebitos = dadosExtrato.filter(d => d.tipo === "debito" && d.debito > 0);
    const qtdeAp01 = ultimaAp01.qtdePrestacoes || 0;
    
    // Pular as parcelas já usadas no Apêndice 01
    const debitosRestantes = todosDebitos.slice(qtdeAp01);
    
    if (debitosRestantes.length === 0) {
      alert(`O Extrato tem ${todosDebitos.length} débitos e o Apêndice 01 usou ${qtdeAp01}. Não há parcelas restantes.`);
      return;
    }
    
    const novasLinhas: LinhaCalculo[] = [];
    const dataInicio = ultimaAp01.data; // Data da última parcela do Ap.01
    
    // 1ª LINHA: data da última parcela do Ap.01 + saldo devedor
    novasLinhas.push(criarLinha(1, dataInicio, ultimaAp01.saldoDevedor));
    
    // DEMAIS LINHAS: datas sequenciais mês a mês, valores dos débitos restantes
    debitosRestantes.forEach((d, idx) => {
      const dataSeq = calcularDataVencimento(dataInicio, idx + 1); // +1 porque a 1ª já é dataInicio
      novasLinhas.push(criarLinha(idx + 2, dataSeq, d.debito));
    });
    
    // Salvar como dados importados
    localStorage.setItem(LS_KEY_DADOS, JSON.stringify(dadosExtrato));
    
    setLinhas(novasLinhas);
    setQtdeParcelasIndevidas(novasLinhas.length);
    
    // Buscar INPC
    buscarFatoresINPC(novasLinhas.map(l => l.dataPagto));
  }, [dataCitacao, dataCalculo, taxaJurosMora, calcularDataVencimento, buscarFatoresINPC]);

  // Recalcular linhas manualmente (modo sem importação)
  const recalcularLinhas = useCallback(() => {
    const dataUltimaParcela = calcularDataUltimaParcela();
    const novasLinhas: LinhaCalculo[] = [];
    const saldo = loadSaldoDevedorAp01();
    
    for (let i = 0; i < qtdeParcelasIndevidas; i++) {
      const dataVenc = calcularDataVencimento(dataUltimaParcela, i);
      const valor = i === 0 && saldo > 0 ? saldo : prestacaoPaga;
      novasLinhas.push(criarLinha(i + 1, dataVenc, valor));
    }
    
    setLinhas(novasLinhas);
    buscarFatoresINPC(novasLinhas.map(l => l.dataPagto));
  }, [qtdeParcelasIndevidas, prestacaoPaga, dataCitacao, dataCalculo, taxaJurosMora, calcularDataUltimaParcela, calcularDataVencimento, buscarFatoresINPC]);

  // Recalcular com novos fatores do BCB
  const recalcularComBCB = () => {
    buscarFatoresINPC(linhas.map(l => l.dataPagto));
  };

  // Limpar dados importados
  const limparImportacao = () => {
    localStorage.removeItem(LS_KEY_DADOS);
    recalcularLinhas();
  };

  // Importar TODOS os dados filtrados do Extrato (sem pular parcelas do Ap.01)
  const importarDoExtrato = () => {
    const dados = loadDadosFiltradosExtrato();
    if (!dados || dados.length === 0) {
      alert("Nenhum dado filtrado encontrado. Abra o Extrato, aplique os filtros desejados e volte aqui.");
      return;
    }
    const debitos = dados.filter(d => d.tipo === "debito" && d.debito > 0);
    if (debitos.length === 0) {
      alert("Nenhum débito encontrado nos dados filtrados do Extrato.");
      return;
    }
    localStorage.setItem(LS_KEY_DADOS, JSON.stringify(dados));
    
    const novasLinhas: LinhaCalculo[] = debitos.map((d, idx) =>
      criarLinha(idx + 1, d.data, d.debito)
    );
    
    setLinhas(novasLinhas);
    setQtdeParcelasIndevidas(novasLinhas.length);
    buscarFatoresINPC(novasLinhas.map(l => l.dataPagto));
  };

  // Totais
  const totais = useMemo(() => ({
    totalPago: linhas.reduce((s, l) => s + l.valorPago, 0),
    totalCorrigido: linhas.reduce((s, l) => s + l.valorCorrigido, 0),
    totalJurosMora: linhas.reduce((s, l) => s + l.valorJurosMora, 0),
    totalRestituir: linhas.reduce((s, l) => s + l.totalCreditoRestituir, 0),
    totalRestituirDobro: linhas.reduce((s, l) => s + l.totalCreditoRestituirDobro, 0),
    totalCompras: linhas.reduce((s, l) => s + l.comprasCorrigidas, 0),
    totalCompensar: linhas.reduce((s, l) => s + l.totalDebitoCompensar, 0),
  }), [linhas]);

  // Exportar XLSX
  const exportXLSX = () => {
    const wsData = [
      ["PERÍCIA ESPECIALIZADA"],
      ["APÊNDICE 02: DEMONSTRATIVO DO EXCESSO PAGO E LIQUIDAÇÃO DA SENTENÇA"],
      [],
      [`Requerente: ${requerente}`],
      [`Requerido: ${requerido}`],
      [`Índice de Correção: INPC (Banco Central do Brasil - Série 188)`],
      [`Data do Cálculo: ${dataCalculo}`],
      [],
      ["", "LIQUIDAÇÃO DO CRÉDITO A RESTITUIR [+]", "", "", "", "", "", "", "", "", "", "APURAÇÃO DO DÉBITO A COMPENSAR [-]"],
      [],
      ["Qtde", "Data Pagto", "Valor Pago", "Fator INPC", "Valor Corrigido", "Data Citação", "Data Cálculo", "Taxa (%)", "Dias", "Juros Mora", "Total Restituir", "Em Dobro", "Compras", "Fator", "Corrigidas", "Compensar"],
      ...linhas.map(l => [
        l.qtde, l.dataPagto, l.valorPago.toFixed(2), l.fatorINPC.toFixed(4),
        l.valorCorrigido.toFixed(2), l.dataCitacao, l.dataCalculo,
        `${l.taxaJurosMora}%`, l.diasJurosMora, l.valorJurosMora.toFixed(2),
        l.totalCreditoRestituir.toFixed(2), l.totalCreditoRestituirDobro.toFixed(2),
        l.compras || "", l.fatorCompras.toFixed(4), l.comprasCorrigidas.toFixed(2),
        l.totalDebitoCompensar.toFixed(2),
      ]),
      [],
      ["TOTAIS", "", totais.totalPago.toFixed(2), "", totais.totalCorrigido.toFixed(2), "", "", "", "", totais.totalJurosMora.toFixed(2), totais.totalRestituir.toFixed(2), totais.totalRestituirDobro.toFixed(2), "", "", totais.totalCompras.toFixed(2), totais.totalCompensar.toFixed(2)],
    ];
    const ws = XLSX.utils.aoa_to_sheet(wsData);
    ws["!cols"] = Array(16).fill({ wch: 12 });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Apêndice 02");
    XLSX.writeFile(wb, `apendice02-liquidacao-sentenca.xlsx`);
  };

  // Exportar PDF
  const exportPDF = () => {
    const printContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Apêndice 02 - Liquidação de Sentença</title>
        <style>
          body { font-family: Arial, sans-serif; font-size: 7px; margin: 10px; }
          h1 { font-size: 10px; text-align: center; margin-bottom: 3px; color: #666; }
          h2 { font-size: 11px; text-align: center; margin-bottom: 10px; color: #000; }
          .info { font-size: 8px; margin-bottom: 5px; }
          table { width: 100%; border-collapse: collapse; font-size: 6px; }
          th, td { border: 1px solid #000; padding: 2px; text-align: center; }
          th { background: #e0e0e0; font-weight: bold; }
          .section-header { background: #4a90d9; color: white; }
          .right { text-align: right; }
          .total { font-weight: bold; background: #f0f0f0; }
          .credito { background: #e8f5e9; }
          .debito { background: #ffebee; }
          @media print { body { margin: 3mm; } @page { size: landscape; } }
        </style>
      </head>
      <body>
        <h1>PERÍCIA ESPECIALIZADA</h1>
        <h2>APÊNDICE 02: DEMONSTRATIVO DO EXCESSO PAGO E LIQUIDAÇÃO DA SENTENÇA</h2>
        <p class="info"><strong>Requerente:</strong> ${requerente} | <strong>Requerido:</strong> ${requerido}</p>
        <p class="info"><strong>Índice de Correção:</strong> INPC (Banco Central do Brasil - Série 188) | <strong>Data do Cálculo:</strong> ${dataCalculo}</p>
        <table>
          <thead>
            <tr>
              <th colspan="12" class="section-header credito">LIQUIDAÇÃO DO CRÉDITO A RESTITUIR [+]</th>
              <th colspan="4" class="section-header debito">APURAÇÃO DO DÉBITO A COMPENSAR [-]</th>
            </tr>
            <tr>
              <th>Qtde</th><th>Data Pagto</th><th>Valor Pago</th><th>Fator INPC</th>
              <th>Valor Corrigido</th><th>Data Citação</th><th>Data Cálculo</th>
              <th>Taxa</th><th>Dias</th><th>Juros Mora</th><th>Total Restituir</th>
              <th>Em Dobro</th><th>Compras</th><th>Fator</th><th>Corrigidas</th><th>Compensar</th>
            </tr>
          </thead>
          <tbody>
            ${linhas.map((l, i) => `
              <tr${i === 0 && saldoDevedorAp01 > 0 ? ' style="background:#fffde7"' : ''}>
                <td>${l.qtde}</td><td>${l.dataPagto}</td>
                <td class="right">${brl(l.valorPago)}</td>
                <td>${l.fatorINPC.toFixed(4)}</td>
                <td class="right">${brl(l.valorCorrigido)}</td>
                <td>${l.dataCitacao}</td><td>${l.dataCalculo}</td>
                <td>${l.taxaJurosMora}%</td><td>${l.diasJurosMora}</td>
                <td class="right">${brl(l.valorJurosMora)}</td>
                <td class="right">${brl(l.totalCreditoRestituir)}</td>
                <td class="right">${brl(l.totalCreditoRestituirDobro)}</td>
                <td class="right">${l.compras || ""}</td>
                <td>${l.fatorCompras.toFixed(4)}</td>
                <td class="right">${brl(l.comprasCorrigidas)}</td>
                <td class="right">${brl(l.totalDebitoCompensar)}</td>
              </tr>
            `).join("")}
          </tbody>
          <tfoot>
            <tr class="total">
              <td colspan="2">TOTAIS</td>
              <td class="right">${brl(totais.totalPago)}</td><td></td>
              <td class="right">${brl(totais.totalCorrigido)}</td><td colspan="4"></td>
              <td class="right">${brl(totais.totalJurosMora)}</td>
              <td class="right">${brl(totais.totalRestituir)}</td>
              <td class="right">${brl(totais.totalRestituirDobro)}</td>
              <td colspan="2"></td>
              <td class="right">${brl(totais.totalCompras)}</td>
              <td class="right">${brl(totais.totalCompensar)}</td>
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

  // Status badge do INPC
  const StatusBadge = () => {
    switch (statusINPC) {
      case "loading":
        return (<div className="flex items-center gap-2 text-yellow-400 text-xs"><Spinner className="w-3 h-3" /><span>Consultando BCB...</span></div>);
      case "success":
        return (<div className="flex items-center gap-2 text-green-400 text-xs"><CheckCircle className="w-3 h-3" /><span>INPC atualizado ({ultimaAtualizacao})</span></div>);
      case "error":
        return (<div className="flex items-center gap-2 text-red-400 text-xs"><AlertCircle className="w-3 h-3" /><span>{erroINPC || "Erro ao consultar BCB"}</span></div>);
      default:
        return (<div className="flex items-center gap-2 text-[var(--muted)] text-xs"><Wifi className="w-3 h-3" /><span>Aguardando consulta ao BCB</span></div>);
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
            <h2 className="text-lg font-bold text-white">Apêndice 02</h2>
            <p className="text-xs text-[var(--muted)]">Demonstrativo do Excesso Pago e Liquidação de Sentença</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="primary" onClick={importarDoExtrato} className="bg-cyan-600 hover:bg-cyan-700">
            <Import className="w-4 h-4" /> Importar do Extrato
          </Button>
          <Button variant="primary" onClick={recalcularComDadosAp01} className="bg-orange-600 hover:bg-orange-700">
            <Calculator className="w-4 h-4" /> Recalcular (Ap.01→02)
          </Button>
          <Button variant="secondary" onClick={recalcularComBCB} disabled={statusINPC === "loading"}>
            {statusINPC === "loading" ? <Spinner className="w-4 h-4" /> : <RefreshCw className="w-4 h-4" />}
            Atualizar INPC
          </Button>
          <Button variant="secondary" onClick={exportXLSX}>
            <FileSpreadsheet className="w-4 h-4" /> XLSX
          </Button>
          <Button variant="secondary" onClick={exportPDF}>
            <FileDown className="w-4 h-4" /> PDF
          </Button>
        </div>
      </div>

      {/* Status do INPC */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-blue-400" />
              <div>
                <p className="text-sm font-medium text-white">Índice de Correção: INPC</p>
                <p className="text-xs text-[var(--muted)]">Banco Central do Brasil - SGS Série 188</p>
              </div>
            </div>
            <StatusBadge />
          </div>
        </CardBody>
      </Card>

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
                    {linhas.length} parcelas indevidas com datas e valores reais
                    {saldoDevedorAp01 > 0 && ` · 1ª linha = Saldo Devedor Ap.01: R$ ${brl(saldoDevedorAp01)}`}
                  </p>
                </div>
              </div>
              <Button variant="ghost" onClick={limparImportacao} className="text-xs text-red-400 hover:text-red-300">
                Limpar importação
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Saldo Devedor do Apêndice 01 */}
      {saldoDevedorAp01 > 0 && (
        <Card>
          <CardBody>
            <div className="flex items-center gap-3">
              <DollarSign className="w-5 h-5 text-yellow-400" />
              <div>
                <p className="text-sm font-medium text-white">Dados do Apêndice 01</p>
                <p className="text-xs text-[var(--muted)]">
                  Última parcela: <span className="text-cyan-400 font-mono font-semibold">{loadUltimaLinhaAp01()?.data || "—"}</span>
                  {" · "}Saldo Devedor: <span className="text-yellow-400 font-mono font-semibold">R$ {brl(saldoDevedorAp01)}</span>
                  {" · "}Parcelas usadas: <span className="text-blue-400 font-mono font-semibold">{loadUltimaLinhaAp01()?.qtdePrestacoes || "—"}</span>
                </p>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Dados do Cabeçalho */}
      <Card>
        <CardHeader>
          <Scale className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-semibold text-white">Parâmetros do Cálculo</span>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <Input label="Requerente" value={requerente} onChange={e => setRequerente(e.target.value)} />
              <Input label="Requerido" value={requerido} onChange={e => setRequerido(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input label="1º Vencimento (Contrato)" value={primeiroVencimentoOriginal} onChange={e => setPrimeiroVencimentoOriginal(e.target.value)} />
              <Input label="Qtde Parcelas Contrato" type="number" value={qtdePrestacoesOriginal} onChange={e => setQtdePrestacoesOriginal(Number(e.target.value))} />
              <Input label="Qtde Parcelas Indevidas" type="number" value={qtdeParcelasIndevidas} onChange={e => setQtdeParcelasIndevidas(Number(e.target.value))} />
              <Input label="Prestação Paga" type="number" step="0.01" value={prestacaoPaga} onChange={e => setPrestacaoPaga(Number(e.target.value))} />
              <Input label="Data da Citação" value={dataCitacao} onChange={e => setDataCitacao(e.target.value)} />
              <Input label="Data do Cálculo" value={dataCalculo} onChange={e => setDataCalculo(e.target.value)} />
              <Input label="Taxa Juros Mora (% a.m.)" type="number" step="0.01" value={taxaJurosMora} onChange={e => setTaxaJurosMora(Number(e.target.value))} />
              <div className="flex items-end">
                <div className="text-xs text-[var(--muted)]">
                  <span className="block">Início das parcelas indevidas:</span>
                  <span className="text-cyan-400 font-mono font-semibold">{calcularDataUltimaParcela()}</span>
                </div>
              </div>
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            {!temDadosImportados && (
              <Button variant="secondary" onClick={recalcularLinhas} disabled={statusINPC === "loading"}>
                <Calculator className="w-4 h-4" /> Recalcular Parcelas
              </Button>
            )}
            <Button variant="primary" onClick={recalcularComBCB} disabled={statusINPC === "loading"}>
              <RefreshCw className="w-4 h-4" /> Atualizar INPC
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Pago", value: `R$ ${brl(totais.totalPago)}`, icon: DollarSign, color: "text-blue-400" },
          { label: "Total Corrigido", value: `R$ ${brl(totais.totalCorrigido)}`, icon: TrendingUp, color: "text-purple-400" },
          { label: "Total a Restituir", value: `R$ ${brl(totais.totalRestituir)}`, icon: TrendingUp, color: "text-green-400" },
          { label: "Total em Dobro", value: `R$ ${brl(totais.totalRestituirDobro)}`, icon: Scale, color: "text-orange-400" },
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
          <span className="text-sm font-semibold text-white">Demonstrativo de Liquidação</span>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th colSpan={12} className="px-2 py-2 text-center bg-green-500/10 text-green-400 text-xs font-semibold">
                  LIQUIDAÇÃO DO CRÉDITO A RESTITUIR [+]
                </th>
                <th colSpan={4} className="px-2 py-2 text-center bg-red-500/10 text-red-400 text-xs font-semibold">
                  APURAÇÃO DO DÉBITO A COMPENSAR [-]
                </th>
              </tr>
              <tr className="border-b border-[var(--border)] text-[10px] text-[var(--muted)] bg-white/2">
                <th className="px-2 py-2 font-medium">Qtde</th>
                <th className="px-2 py-2 font-medium">Data Pagto</th>
                <th className="px-2 py-2 font-medium text-right">Valor Pago</th>
                <th className="px-2 py-2 font-medium">Fator INPC</th>
                <th className="px-2 py-2 font-medium text-right">Valor Corrigido</th>
                <th className="px-2 py-2 font-medium">Data Citação</th>
                <th className="px-2 py-2 font-medium">Data Cálculo</th>
                <th className="px-2 py-2 font-medium">Taxa</th>
                <th className="px-2 py-2 font-medium">Dias</th>
                <th className="px-2 py-2 font-medium text-right">Juros Mora</th>
                <th className="px-2 py-2 font-medium text-right">Total Restituir</th>
                <th className="px-2 py-2 font-medium text-right">Em Dobro</th>
                <th className="px-2 py-2 font-medium text-right">Compras</th>
                <th className="px-2 py-2 font-medium">Fator</th>
                <th className="px-2 py-2 font-medium text-right">Corrigidas</th>
                <th className="px-2 py-2 font-medium text-right">Compensar</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((l, i) => (
                <tr key={i} className={`border-b border-[var(--border)]/40 hover:bg-white/2 ${i === 0 && saldoDevedorAp01 > 0 ? "bg-yellow-500/5" : ""}`}>
                  <td className="px-2 py-1.5 text-center">{l.qtde}</td>
                  <td className="px-2 py-1.5 text-center font-mono">{l.dataPagto}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-blue-400">{brl(l.valorPago)}</td>
                  <td className="px-2 py-1.5 text-center font-mono text-cyan-400">{l.fatorINPC.toFixed(4)}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-purple-400">{brl(l.valorCorrigido)}</td>
                  <td className="px-2 py-1.5 text-center font-mono text-[var(--muted)]">{l.dataCitacao}</td>
                  <td className="px-2 py-1.5 text-center font-mono text-[var(--muted)]">{l.dataCalculo}</td>
                  <td className="px-2 py-1.5 text-center">{l.taxaJurosMora}%</td>
                  <td className="px-2 py-1.5 text-center">{l.diasJurosMora}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-yellow-400">{brl(l.valorJurosMora)}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-green-400 font-semibold">{brl(l.totalCreditoRestituir)}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-orange-400">{brl(l.totalCreditoRestituirDobro)}</td>
                  <td className="px-2 py-1.5 text-right font-mono">{l.compras || ""}</td>
                  <td className="px-2 py-1.5 text-center font-mono text-[var(--muted)]">{l.fatorCompras.toFixed(4)}</td>
                  <td className="px-2 py-1.5 text-right font-mono">{brl(l.comprasCorrigidas)}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-red-400">{brl(l.totalDebitoCompensar)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-[var(--border)] bg-white/3">
                <td colSpan={2} className="px-2 py-2 text-xs font-semibold text-[var(--muted)] uppercase">Totais</td>
                <td className="px-2 py-2 text-right font-mono font-bold text-blue-400">{brl(totais.totalPago)}</td>
                <td></td>
                <td className="px-2 py-2 text-right font-mono font-bold text-purple-400">{brl(totais.totalCorrigido)}</td>
                <td colSpan={4}></td>
                <td className="px-2 py-2 text-right font-mono font-bold text-yellow-400">{brl(totais.totalJurosMora)}</td>
                <td className="px-2 py-2 text-right font-mono font-bold text-green-400">{brl(totais.totalRestituir)}</td>
                <td className="px-2 py-2 text-right font-mono font-bold text-orange-400">{brl(totais.totalRestituirDobro)}</td>
                <td colSpan={2}></td>
                <td className="px-2 py-2 text-right font-mono font-bold">{brl(totais.totalCompras)}</td>
                <td className="px-2 py-2 text-right font-mono font-bold text-red-400">{brl(totais.totalCompensar)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>
    </div>
  );
}
