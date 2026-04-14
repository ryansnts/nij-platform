import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { docs } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Upload as UploadIcon, FileText, X, Tag, Plus, CheckCircle, AlertCircle, StopCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

const PROFILES = [
  { id: "auto",                    label: "1 - Detecção Automática" },
  { id: "historico_creditos_inss", label: "2 - Histórico de Crédito INSS" },
  { id: "demonstrativo_siape",     label: "3 - Demonstrativo Rendimento Anual (SIAPE/IFAM)" },
  { id: "contracheque_amazonprev", label: "4 - Fundação AmazonPrev" },
  { id: "contracheque_pmm",        label: "5 - Contracheque PMM AM" },
  { id: "contracheque_semad",      label: "6 - Contracheque SEMAD/Pref. Manaus" },
  { id: "ficha_financeira_semad",  label: "7 - Ficha Financeira SEMAD" },
  { id: "contracheque_sead",       label: "8 - Contracheque SEAD/Governo AM" },
  { id: "ficha_financeira_sead",   label: "9 - Ficha Financeira SEAD/Governo AM" },
  { id: "contracheque_figueiredo", label: "10 - Pref. Munic. Pres. Figueiredo" },
  { id: "extrato_bancario",        label: "11 - Extratos Bancários" },
  { id: "fatura_ole_santander",    label: "12 - Fatura Cartão Olé-Santander" },
  // Legado
  { id: "contracheque",            label: "Contracheque Genérico" },
  { id: "inss_cartao",             label: "Extrato INSS / Cartão RCC/RMC" },
  { id: "fatura",                  label: "Fatura Cartão Consignado" },
];

type Status = "idle" | "uploading" | "polling" | "done" | "error" | "cancelled";

interface ProgressInfo {
  progress: number;
  message: string;
  currentPage: number;
  totalPages: number;
}

export default function Upload() {
  const nav = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState("auto");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [kwInput, setKwInput] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [drag, setDrag] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [docId, setDocId] = useState<string | null>(null);
  const [progressInfo, setProgressInfo] = useState<ProgressInfo>({ progress: 0, message: "", currentPage: 0, totalPages: 0 });
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

  // Timer para tempo decorrido
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (status === "polling" && startTime) {
      interval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [status, startTime]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const estimateRemainingTime = () => {
    if (progressInfo.progress <= 0 || elapsedTime <= 0) return null;
    const estimatedTotal = (elapsedTime / progressInfo.progress) * 100;
    const remaining = Math.max(0, Math.floor(estimatedTotal - elapsedTime));
    return remaining;
  };

  const addKw = () => {
    const k = kwInput.trim().toLowerCase();
    if (k && !keywords.includes(k)) { setKeywords(p => [...p, k]); setKwInput(""); }
  };

  const cancelProcessing = async () => {
    if (!docId) return;
    try {
      await docs.cancel(docId);
      setStatus("cancelled");
      setErrMsg("Processamento cancelado pelo usuário");
    } catch (e: any) {
      console.error("Erro ao cancelar:", e);
    }
  };

  const process = async () => {
    if (!file) return;
    setStatus("uploading");
    setErrMsg("");
    setProgressInfo({ progress: 0, message: "Enviando arquivo...", currentPage: 0, totalPages: 0 });
    setStartTime(Date.now());
    setElapsedTime(0);
    
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("extraction_profile", profile);
      if (keywords.length) fd.append("search_keywords", JSON.stringify(keywords));

      const { data: doc } = await docs.upload(fd);
      setDocId(doc.id);
      setStatus("polling");
      setProgressInfo({ progress: 5, message: "Iniciando processamento...", currentPage: 0, totalPages: 0 });

      // Poll até completar
      for (let i = 0; i < 300; i++) { // 300 * 2s = 10 minutos máximo
        await new Promise(r => setTimeout(r, 2000));
        const { data: updated } = await docs.get(doc.id);
        
        // Atualizar progresso
        setProgressInfo({
          progress: updated.progress || 0,
          message: updated.progress_message || "Processando...",
          currentPage: updated.current_page || 0,
          totalPages: updated.total_pages || 0,
        });
        
        if (updated.status === "completed") {
          setStatus("done");
          setProgressInfo({ progress: 100, message: "Concluído!", currentPage: 0, totalPages: 0 });
          setTimeout(() => nav(`/resultado/${doc.id}`), 800);
          return;
        }
        if (updated.status === "error") {
          throw new Error(updated.error_message || "Erro no processamento");
        }
        if (updated.status === "cancelled") {
          setStatus("cancelled");
          setErrMsg("Processamento cancelado");
          return;
        }
      }
      throw new Error("Timeout: processamento demorou mais que o esperado (10 min)");
    } catch (e: any) {
      setStatus("error");
      setErrMsg(e.message ?? "Erro desconhecido");
    }
  };

  const resetForm = () => {
    setStatus("idle");
    setFile(null);
    setDocId(null);
    setProgressInfo({ progress: 0, message: "", currentPage: 0, totalPages: 0 });
    setElapsedTime(0);
    setStartTime(null);
    setErrMsg("");
  };

  const remainingTime = estimateRemainingTime();

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="text-center py-4">
        <h2 className="text-2xl font-bold text-white">
          Análise de Documentos — <span className="gradient-text">CLIENTES</span>
        </h2>
        <p className="text-sm text-[var(--muted)] mt-1">
          Faça upload do PDF para extrair dados financeiros e identificar descontos indevidos
        </p>
      </div>

      {/* Perfil */}
      <Card>
        <CardBody className="space-y-3">
          <label className="text-xs text-[var(--muted)] font-medium">Perfil de Extração</label>
          <select value={profile} onChange={e => setProfile(e.target.value)}
            disabled={status !== "idle"}
            className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 disabled:opacity-50">
            {PROFILES.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </CardBody>
      </Card>

      {/* Keywords */}
      <Card>
        <CardBody className="space-y-3">
          <p className="text-xs text-[var(--muted)] font-medium">Palavras-chave de busca <span className="text-[var(--muted)]">(opcional)</span></p>
          <div className="flex gap-2">
            <input value={kwInput} onChange={e => setKwInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addKw())}
              disabled={status !== "idle"}
              placeholder="Ex: seguro, tarifa, capitalização..."
              className="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[var(--muted)] focus:outline-none focus:border-blue-500 disabled:opacity-50" />
            <Button variant="secondary" onClick={addKw} disabled={!kwInput.trim() || status !== "idle"}>
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          {keywords.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {keywords.map(k => (
                <span key={k} className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs">
                  <Tag className="w-3 h-3" />{k}
                  <button onClick={() => setKeywords(p => p.filter(x => x !== k))} disabled={status !== "idle"} className="ml-1 hover:text-red-400 disabled:opacity-50">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); if (status === "idle") setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); if (status === "idle") { const f = e.dataTransfer.files[0]; if (f?.type === "application/pdf") setFile(f); } }}
        onClick={() => !file && status === "idle" && inputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-xl p-10 flex flex-col items-center gap-3 transition-colors",
          status === "idle" ? "cursor-pointer" : "cursor-not-allowed opacity-60",
          drag ? "border-blue-500 bg-blue-500/5" : "border-[var(--border)] hover:border-blue-500/50 hover:bg-white/2"
        )}
      >
        <input ref={inputRef} type="file" accept=".pdf" className="hidden" disabled={status !== "idle"}
          onChange={e => e.target.files?.[0] && setFile(e.target.files[0])} />
        <div className="w-14 h-14 rounded-xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center">
          <UploadIcon className="w-6 h-6 text-blue-500" />
        </div>
        <p className="text-sm font-medium text-white">Arraste o PDF aqui ou clique para selecionar</p>
        <p className="text-xs text-[var(--muted)]">Contracheques, faturas e extratos</p>
      </div>

      {/* File preview */}
      {file && (
        <div className="surface rounded-xl p-4 flex items-center gap-3">
          <FileText className="w-5 h-5 text-blue-500 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{file.name}</p>
            <p className="text-xs text-[var(--muted)]">{(file.size / 1024).toFixed(0)} KB</p>
          </div>
          {status === "idle" && (
            <button onClick={() => setFile(null)} className="text-[var(--muted)] hover:text-white">
              <X className="w-4 h-4" />
            </button>
          )}
          {(status === "uploading" || status === "polling") && <Spinner className="w-5 h-5" />}
          {status === "done" && <CheckCircle className="w-5 h-5 text-green-500" />}
          {status === "error" && <AlertCircle className="w-5 h-5 text-red-500" />}
          {status === "cancelled" && <StopCircle className="w-5 h-5 text-orange-500" />}
        </div>
      )}

      {/* Barra de progresso */}
      {(status === "uploading" || status === "polling") && (
        <Card>
          <CardBody className="space-y-4">
            {/* Header com tempo */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Spinner className="w-4 h-4" />
                <span className="text-sm font-medium text-white">Processando...</span>
              </div>
              <div className="flex items-center gap-4 text-xs text-[var(--muted)]">
                <div className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Decorrido: {formatTime(elapsedTime)}</span>
                </div>
                {remainingTime !== null && remainingTime > 0 && (
                  <span>Restante: ~{formatTime(remainingTime)}</span>
                )}
              </div>
            </div>
            
            {/* Barra de progresso */}
            <div className="space-y-2">
              <div className="h-3 bg-[var(--bg)] rounded-full overflow-hidden border border-[var(--border)]">
                <div 
                  className="h-full bg-gradient-to-r from-blue-600 to-blue-400 transition-all duration-500 ease-out"
                  style={{ width: `${progressInfo.progress}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-[var(--muted)]">{progressInfo.message}</span>
                <span className="text-blue-400 font-mono font-semibold">{progressInfo.progress}%</span>
              </div>
            </div>
            
            {/* Info de páginas */}
            {progressInfo.totalPages > 0 && (
              <div className="flex items-center justify-center gap-2 text-xs text-[var(--muted)]">
                <span>Página {progressInfo.currentPage} de {progressInfo.totalPages}</span>
              </div>
            )}
            
            {/* Botão cancelar */}
            <Button 
              variant="secondary" 
              onClick={cancelProcessing}
              className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              <StopCircle className="w-4 h-4" /> Cancelar Processamento
            </Button>
          </CardBody>
        </Card>
      )}

      {(status === "error" || status === "cancelled") && (
        <div className={cn(
          "border rounded-xl p-4 text-sm",
          status === "error" ? "bg-red-500/10 border-red-500/20 text-red-400" : "bg-orange-500/10 border-orange-500/20 text-orange-400"
        )}>
          {errMsg}
          <button onClick={resetForm} className="ml-3 underline">Tentar novamente</button>
        </div>
      )}

      {file && status === "idle" && (
        <Button onClick={process} className="w-full">
          Processar documento
        </Button>
      )}
    </div>
  );
}
