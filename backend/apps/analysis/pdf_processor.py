"""
NIJ PDF Processor — Python/pdfplumber + pytesseract
Migração e melhoria do pdf-processor.ts original.
"""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field
from typing import Optional
import pdfplumber
import pytesseract
from PIL import Image
import io

logger = logging.getLogger(__name__)

BLACKLIST_TERMS = {
    "TOTAL DA FATURA ANTERIOR", "TOTAL FATURA ANTERIOR", "IOF",
    "IOF RETIRADA-PAIS", "IOF ROTATIVO", "DIFERENCA DE IOF",
    "ENCARGOS", "ENCARGOS DE FINANCIAMENTO", "ENCARGOS FINANCIAMENTO ESTORNO",
    "ESTORNO ENCARGO FINANC", "ESTORNO ENCARGOS", "ESTORNO PAGAMENTO PRESUMIDO",
    "DEBITO DE IOF",
}


@dataclass
class Transacao:
    data: str
    descricao: str
    valor: float
    tipo: str  # "debito" | "credito"
    codigo_rmc: Optional[str] = None


@dataclass
class Contrato:
    numero: str
    banco: str
    tipo: str
    parcela: int = 0
    total_parcelas: int = 0
    valor_parcela: float = 0.0
    saldo_devedor: float = 0.0
    taxa_juros: float = 0.0


@dataclass
class DescontoIndevido:
    descricao: str
    valor: float
    tipo: str
    status: str = "identificado"


@dataclass
class ExtractedData:
    nome: str = ""
    cpf: str = ""
    matricula: str = ""
    orgao: str = ""
    competencia: str = ""
    valor_bruto: Optional[float] = None
    valor_liquido: Optional[float] = None
    margem_consignavel: Optional[float] = None
    margem_utilizada: Optional[float] = None
    margem_disponivel: Optional[float] = None
    transacoes: list[Transacao] = field(default_factory=list)
    contratos: list[Contrato] = field(default_factory=list)
    descontos_indevidos: list[DescontoIndevido] = field(default_factory=list)
    codigos_rmc: list[dict] = field(default_factory=list)
    raw_text: str = ""


def _parse_currency(value_str: str) -> float:
    return float(value_str.replace(".", "").replace(",", "."))


def _is_blacklisted(desc: str) -> bool:
    normalized = re.sub(r"\s+", " ", desc.strip().upper())
    return any(
        normalized == term or normalized.startswith(term + " ")
        for term in BLACKLIST_TERMS
    )


def _extract_text_pdfplumber(file_bytes: bytes) -> str:
    """Extract text using pdfplumber (better than pdfjs for server-side)."""
    full_text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            full_text += text + "\n\n"
    return full_text


def _extract_text_ocr(file_bytes: bytes) -> str:
    """Fallback OCR using pytesseract when pdfplumber yields insufficient text."""
    full_text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            img = page.to_image(resolution=300).original
            text = pytesseract.image_to_string(img, lang="por")
            full_text += text + "\n\n"
    return full_text


def extract_text(file_bytes: bytes) -> str:
    text = _extract_text_pdfplumber(file_bytes)
    letter_count = len(re.findall(r"[a-zA-ZÀ-ÿ0-9]", text))
    if letter_count < 100:
        logger.info("Texto insuficiente (%d chars), usando OCR...", letter_count)
        text = _extract_text_ocr(file_bytes)
    return text


def _extract_field(text: str, *patterns: str) -> str:
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _extract_currency(text: str, *patterns: str) -> Optional[float]:
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return _parse_currency(m.group(1))
            except (ValueError, IndexError):
                continue
    return None


def _parse_personal_info(text: str, data: ExtractedData) -> None:
    data.nome = _extract_field(
        text,
        r"(?:nome|servidor|benefici[aá]rio)[:\s]+([A-ZÀ-Ú][A-ZÀ-Ú\s]{5,60})",
        r"^([A-ZÀ-Ú][A-ZÀ-Ú\s]{5,50})\s*$",
    )
    data.cpf = _extract_field(
        text,
        r"CPF[:\s]*([\d]{3}\.[\d]{3}\.[\d]{3}-[\d]{2})",
        r"CPF[:\s]*([\d]{11})",
    )
    data.matricula = _extract_field(
        text,
        r"matr[íi]cula[:\s]*([\w\d-]{4,20})",
        r"(?:n[°ºo]|num)[:\s]*([\d]{5,12})",
    )
    data.orgao = _extract_field(
        text,
        r"[óo]rg[ãa]o[:\s]+([A-ZÀ-Ú][^\n]{3,60})",
        r"(?:empresa|institui[çc][ãa]o)[:\s]+([A-ZÀ-Ú][^\n]{3,60})",
    )
    data.competencia = _extract_field(
        text,
        r"compet[êe]ncia[:\s]*(\d{2}/\d{4})",
        r"refer[êe]ncia[:\s]*(\d{2}/\d{4})",
        r"per[íi]odo[:\s]*(\d{2}/\d{4})",
    )
    data.valor_bruto = _extract_currency(
        text,
        r"(?:total\s+)?(?:bruto|vencimentos)[:\s]*R?\$?\s*([\d.,]+)",
        r"sal[aá]rio\s+bruto[:\s]*R?\$?\s*([\d.,]+)",
    )
    data.valor_liquido = _extract_currency(
        text,
        r"(?:total\s+)?l[íi]quido[:\s]*R?\$?\s*([\d.,]+)",
        r"valor\s+l[íi]quido[:\s]*R?\$?\s*([\d.,]+)",
    )
    data.margem_consignavel = _extract_currency(
        text, r"margem\s+consign[aá]vel[:\s]*R?\$?\s*([\d.,]+)"
    )
    data.margem_utilizada = _extract_currency(
        text, r"margem\s+utilizada[:\s]*R?\$?\s*([\d.,]+)"
    )
    data.margem_disponivel = _extract_currency(
        text,
        r"margem\s+dispon[íi]vel[:\s]*R?\$?\s*([\d.,]+)",
        r"saldo\s+(?:de\s+)?margem[:\s]*R?\$?\s*([\d.,]+)",
    )


def _parse_contracheque(text: str, competencia: str) -> list[Transacao]:
    transacoes: list[Transacao] = []
    lines = text.split("\n")
    data_ref = competencia or f"01/{__import__('datetime').date.today().year}"

    has_header = any(
        ("CÓDIGO" in l.upper() or "CODIGO" in l.upper()) and
        ("GANHOS" in l.upper() or "DESCONTOS" in l.upper() or "VENCIMENTOS" in l.upper())
        for l in lines
    )
    if not has_header:
        return []

    for line in lines:
        trimmed = line.strip()
        if len(trimmed) < 10:
            continue
        code_m = re.match(r"^(\d{1,6})\s+", trimmed)
        if not code_m:
            continue
        codigo = code_m.group(1)
        after_code = trimmed[len(code_m.group(0)):]
        if not re.match(r"[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-z]", after_code):
            continue

        values = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", after_code)
        if not values:
            continue

        first_val_idx = after_code.index(values[0])
        descricao = after_code[:first_val_idx].strip()
        descricao = re.sub(r"\s+[PVDGHQ]\s*$", "", descricao).strip()
        if len(descricao) < 2 or _is_blacklisted(descricao):
            continue

        parsed_vals = [_parse_currency(v) for v in values]

        if len(parsed_vals) >= 2:
            ganhos, descontos = parsed_vals[-2], parsed_vals[-1]
        elif len(parsed_vals) == 1:
            is_desconto = bool(re.search(
                r"INSS|IRRF|IMPOSTO|CONSIG|PREV|CARTAO|EMPRESTIMO|DESCONTO|PENSAO",
                descricao, re.IGNORECASE
            )) or int(codigo) >= 5000
            ganhos = 0.0 if is_desconto else parsed_vals[0]
            descontos = parsed_vals[0] if is_desconto else 0.0
        else:
            continue

        rmc_code = codigo if codigo in ("217", "268", "322") else None

        if descontos > 0:
            transacoes.append(Transacao(
                data=data_ref, descricao=f"[{codigo}] {descricao}",
                valor=descontos, tipo="debito", codigo_rmc=rmc_code
            ))
        if ganhos > 0:
            transacoes.append(Transacao(
                data=data_ref, descricao=f"[{codigo}] {descricao}",
                valor=ganhos, tipo="credito", codigo_rmc=rmc_code
            ))

    return transacoes


def _parse_contratos(text: str) -> list[Contrato]:
    contratos: list[Contrato] = []
    lines = text.split("\n")
    current: dict = {}

    for line in lines:
        upper = line.upper()
        num_m = re.search(r"(?:contrato|n[°ºo]|c[oó]d)[:\s]*(\d{4,}[\d.-]*)", line, re.IGNORECASE)
        if num_m:
            if current.get("numero") and current.get("valor_parcela"):
                contratos.append(Contrato(**current))
            current = {"numero": num_m.group(1), "banco": "N/I", "tipo": "Consignado",
                       "parcela": 0, "total_parcelas": 0, "valor_parcela": 0.0,
                       "saldo_devedor": 0.0, "taxa_juros": 0.0}

        if current:
            banco_m = re.search(r"(?:BANCO|BCO)[:\s]+([\wÀ-ÿ\s]{3,30})", upper)
            if banco_m:
                current["banco"] = banco_m.group(1).strip().title()
            val_m = re.search(r"(?:valor|vlr|parcela)[:\s]*R?\$?\s*([\d.,]+)", line, re.IGNORECASE)
            if val_m:
                current["valor_parcela"] = _parse_currency(val_m.group(1))
            taxa_m = re.search(r"(?:taxa|juros)[:\s]*(\d+[.,]\d+)\s*%", line, re.IGNORECASE)
            if taxa_m:
                current["taxa_juros"] = float(taxa_m.group(1).replace(",", "."))
            saldo_m = re.search(r"saldo\s+devedor[:\s]*R?\$?\s*([\d.,]+)", line, re.IGNORECASE)
            if saldo_m:
                current["saldo_devedor"] = _parse_currency(saldo_m.group(1))

    if current.get("numero") and current.get("valor_parcela"):
        contratos.append(Contrato(**current))

    return contratos


def _detect_descontos_indevidos(text: str) -> list[DescontoIndevido]:
    descontos: list[DescontoIndevido] = []
    patterns = [
        (r"SEGURO\s+PRESTAMISTA[\s\S]*?R?\$?\s*([\d.,]+)", "Seguro Indevido", "Seguro prestamista não autorizado"),
        (r"TARIFA\s+(?:BANC[AÁ]RIA|MENSAL|ADMINISTRATIVA)[:\s]*R?\$?\s*([\d.,]+)", "Tarifa Indevida", "Cobrança de tarifa bancária"),
        (r"ASSIST[EÊ]NCIA[\s\S]*?R?\$?\s*([\d.,]+)", "Cobrança Indevida", "Assistência não contratada"),
        (r"SEGURO\s+(?:DE\s+)?VIDA[\s\S]*?R?\$?\s*([\d.,]+)", "Seguro", "Seguro de vida vinculado"),
        (r"(?:TAXA|TARIFA)\s+(?:DE\s+)?ABERTURA[\s\S]*?R?\$?\s*([\d.,]+)", "Tarifa Indevida", "Taxa de abertura"),
    ]
    for pattern, tipo, desc in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            try:
                valor = _parse_currency(m.group(1))
                if valor > 0:
                    descontos.append(DescontoIndevido(descricao=desc, valor=valor, tipo=tipo))
            except (ValueError, IndexError):
                continue

    # Juros abusivos (> 2.14% a.m.)
    for m in re.finditer(r"(?:taxa|juros)[:\s]*(\d+[.,]\d+)\s*%\s*(?:a\.?\s*m|mensal)", text, re.IGNORECASE):
        try:
            taxa = float(m.group(1).replace(",", "."))
            if taxa > 2.14:
                descontos.append(DescontoIndevido(
                    descricao=f"Juros acima do teto INSS ({taxa}% a.m.)",
                    valor=0.0, tipo="Juros Abusivos"
                ))
        except ValueError:
            continue

    return descontos


def _parse_contracheque_amazonprev(file_bytes: bytes, progress_callback=None) -> tuple[ExtractedData, list[dict]]:
    """
    Parser específico para contracheques da AmazonPrev.
    
    Formato:
    - Cabeçalho: ÓRGÃO, PODER, MATRÍCULA, NOME DO PENSIONISTA, BANCO, AGÊNCIA, CONTA
    - Competência: MM/AAAA (ex: 1/2024) - MUDA A CADA PÁGINA (está na tabela, não no texto)
    - Tabela: CÓDIGO | Descrição | PARC | INF. | BASE | GANHOS | DESCONTOS
    
    Suporta lotes de até 10 anos de contracheques.
    """
    data = ExtractedData()
    linhas: list[dict] = []
    
    VALUE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")
    # Padrão para data MM/AAAA ou M/AAAA
    DATE_MM_YYYY = re.compile(r"\b(\d{1,2}/\d{4})\b")
    
    processed_keys = set()
    todas_competencias = []
    
    def extract_competencia_from_table(table) -> str | None:
        """Extrai competência da tabela do cabeçalho AmazonPrev.
        
        A tabela tem formato:
        Linha N:   [..., 'COMPETÊNCIA']
        Linha N+1: [..., '1/2024']
        """
        if not table:
            return None
        
        comp_col = -1
        comp_row = -1
        
        # Encontrar coluna com "COMPETÊNCIA"
        for row_idx, row in enumerate(table):
            if not row:
                continue
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).strip().upper() if cell else ""
                if "COMPET" in cell_str:
                    comp_col = col_idx
                    comp_row = row_idx
                    break
            if comp_col >= 0:
                break
        
        if comp_col < 0 or comp_row < 0:
            return None
        
        # Pegar valor da próxima linha na mesma coluna
        if comp_row + 1 < len(table):
            next_row = table[comp_row + 1]
            if next_row and comp_col < len(next_row):
                val = str(next_row[comp_col]).strip() if next_row[comp_col] else ""
                match = DATE_MM_YYYY.search(val)
                if match:
                    return match.group(1)
        
        return None
    
    def normalize_competencia(comp: str) -> str:
        """Normaliza formato: 1/2024 -> 01/2024"""
        parts = comp.split("/")
        if len(parts) == 2:
            mes = parts[0].zfill(2)
            ano = parts[1]
            return f"{mes}/{ano}"
        return comp
    
    def competencia_to_data(comp: str) -> str:
        """
        Converte competência MM/AAAA para data DD/MM/AAAA (último dia do mês).
        Isso é necessário para compatibilidade com os Apêndices que esperam datas completas.
        """
        parts = comp.split("/")
        if len(parts) == 2:
            mes = int(parts[0])
            ano = int(parts[1])
            # Calcular último dia do mês
            if mes == 12:
                ultimo_dia = 31
            else:
                from datetime import date, timedelta
                proximo_mes = date(ano, mes + 1, 1)
                ultimo_dia = (proximo_mes - timedelta(days=1)).day
            return f"{ultimo_dia:02d}/{mes:02d}/{ano}"
        return comp
    
    def add_transacao(competencia: str, codigo: str, desc: str, ganho: float, desconto: float):
        """Adiciona transação de contracheque com a competência específica"""
        # Converter competência para data completa
        data_completa = competencia_to_data(competencia)
        
        key = f"{competencia}|{codigo}|{desc}|{ganho}|{desconto}"
        if key in processed_keys:
            return
        processed_keys.add(key)
        
        if desconto > 0:
            linhas.append({
                "data": data_completa,
                "descricao": f"[{codigo}] {desc}",
                "debito": desconto,
                "credito": 0.0,
                "tipo": "debito",
                "competencia": competencia,  # Manter competência original para referência
            })
            data.transacoes.append(Transacao(
                data=data_completa,
                descricao=f"[{codigo}] {desc}",
                valor=desconto,
                tipo="debito"
            ))
        
        if ganho > 0:
            linhas.append({
                "data": data_completa,
                "descricao": f"[{codigo}] {desc}",
                "debito": 0.0,
                "credito": ganho,
                "tipo": "credito",
                "competencia": competencia,
            })
            data.transacoes.append(Transacao(
                data=data_completa,
                descricao=f"[{codigo}] {desc}",
                valor=ganho,
                tipo="credito"
            ))
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        logger.info("Processando %d páginas de contracheque AmazonPrev", len(pdf.pages))
        
        # Primeira passagem: extrair dados do cabeçalho da primeira página
        first_page_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
        
        # Nome do pensionista
        nome_m = re.search(r"NOME\s+DO\s+PENSIONISTA\s*\n?\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]{5,60})", first_page_text, re.IGNORECASE)
        if nome_m:
            data.nome = nome_m.group(1).strip()
        
        # Matrícula
        matricula_m = re.search(r"MATR[ÍI]CULA\s*\n?\s*([\w\d\-]+)", first_page_text, re.IGNORECASE)
        if matricula_m:
            data.matricula = matricula_m.group(1).strip()
        
        # Órgão
        orgao_m = re.search(r"[ÓO]RG[ÃA]O\s*\n?\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]{3,30})", first_page_text, re.IGNORECASE)
        if orgao_m:
            data.orgao = orgao_m.group(1).strip()
        
        # ── Processar cada página individualmente ────────────
        for page_idx, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            tables = page.extract_tables()
            
            # ── Extrair competência DESTA página ────────────────
            competencia_pagina = None
            
            # Método 1: Extrair da tabela (mais confiável para AmazonPrev)
            for table in tables:
                comp = extract_competencia_from_table(table)
                if comp:
                    competencia_pagina = normalize_competencia(comp)
                    break
            
            # Método 2: Fallback - buscar no texto após "COMPETÊNCIA"
            if not competencia_pagina:
                # Buscar padrão onde COMPETÊNCIA e data estão na mesma linha ou próximas
                comp_patterns = [
                    re.compile(r"COMPET[ÊE]NCIA[:\s]*(\d{1,2}/\d{4})", re.IGNORECASE),
                    re.compile(r"PENS[ÃA]O\s+(\d{1,2}/\d{4})", re.IGNORECASE),
                ]
                for pattern in comp_patterns:
                    match = pattern.search(page_text)
                    if match:
                        competencia_pagina = normalize_competencia(match.group(1))
                        break
            
            # Método 3: Buscar qualquer data MM/AAAA no cabeçalho (primeiras 15 linhas)
            if not competencia_pagina:
                header_lines = page_text.split("\n")[:15]
                for line in header_lines:
                    dates = DATE_MM_YYYY.findall(line)
                    for d in dates:
                        # Validar que é uma data razoável (ano entre 2000 e 2030)
                        parts = d.split("/")
                        if len(parts) == 2:
                            try:
                                mes = int(parts[0])
                                ano = int(parts[1])
                                if 1 <= mes <= 12 and 2000 <= ano <= 2030:
                                    competencia_pagina = normalize_competencia(d)
                                    break
                            except ValueError:
                                continue
                    if competencia_pagina:
                        break
            
            # Se ainda não encontrou, usar última conhecida ou padrão
            if not competencia_pagina:
                competencia_pagina = todas_competencias[-1] if todas_competencias else "01/2024"
                logger.warning("Página %d: Competência não encontrada, usando %s", page_idx + 1, competencia_pagina)
            else:
                if competencia_pagina not in todas_competencias:
                    todas_competencias.append(competencia_pagina)
                logger.info("Página %d: Competência %s", page_idx + 1, competencia_pagina)
            
            # ── Processar tabelas da página ────────────────────
            transacoes_encontradas = False
            
            for table in tables:
                if not table:
                    continue
                
                # Detectar cabeçalho da tabela de transações
                header_row = -1
                codigo_col = -1
                desc_col = -1
                ganhos_col = -1
                descontos_col = -1
                
                for row_idx, row in enumerate(table):
                    if not row:
                        continue
                    cells = [str(c).strip().upper() if c else "" for c in row]
                    
                    for col_idx, cell in enumerate(cells):
                        if "CÓDIGO" in cell or "CODIGO" in cell:
                            codigo_col = col_idx
                            header_row = row_idx
                        elif "DESCRIÇÃO" in cell or "DESCRICAO" in cell:
                            desc_col = col_idx
                        elif "GANHOS" in cell:
                            ganhos_col = col_idx
                        elif "DESCONTOS" in cell:
                            descontos_col = col_idx
                
                if header_row < 0:
                    continue
                
                # Processar linhas de dados (pode ter múltiplas linhas concatenadas com \n)
                for row_idx, row in enumerate(table):
                    if row_idx <= header_row or not row:
                        continue
                    
                    cells = [str(c).strip() if c else "" for c in row]
                    
                    # Verificar se a célula de código tem múltiplas linhas
                    codigo_cell = cells[codigo_col] if codigo_col >= 0 and codigo_col < len(cells) else ""
                    desc_cell = cells[desc_col] if desc_col >= 0 and desc_col < len(cells) else (cells[1] if len(cells) > 1 else "")
                    ganhos_cell = cells[ganhos_col] if ganhos_col >= 0 and ganhos_col < len(cells) else ""
                    descontos_cell = cells[descontos_col] if descontos_col >= 0 and descontos_col < len(cells) else ""
                    
                    # Dividir por quebras de linha se houver múltiplas transações na mesma célula
                    codigos = [c.strip() for c in codigo_cell.split("\n") if c.strip()]
                    descricoes = [d.strip() for d in desc_cell.split("\n") if d.strip()]
                    ganhos_list = [g.strip() for g in ganhos_cell.split("\n") if g.strip()]
                    descontos_list = [d.strip() for d in descontos_cell.split("\n") if d.strip()]
                    
                    # Processar cada transação
                    num_items = max(len(codigos), len(descricoes))
                    
                    for i in range(num_items):
                        codigo = codigos[i] if i < len(codigos) else ""
                        codigo = codigo.replace(" ", "")
                        
                        if not codigo or not re.match(r"^[\d\-]+$", codigo):
                            continue
                        
                        desc = descricoes[i] if i < len(descricoes) else ""
                        desc = re.sub(r"\s+", " ", desc).strip()
                        if not desc or len(desc) < 2:
                            continue
                        
                        # Extrair ganhos
                        ganho = 0.0
                        if i < len(ganhos_list):
                            vm = VALUE_RE.search(ganhos_list[i])
                            if vm:
                                try:
                                    ganho = _parse_currency(vm.group(1))
                                except ValueError:
                                    pass
                        
                        # Extrair descontos
                        desconto = 0.0
                        if i < len(descontos_list):
                            vm = VALUE_RE.search(descontos_list[i])
                            if vm:
                                try:
                                    desconto = _parse_currency(vm.group(1))
                                except ValueError:
                                    pass
                        
                        if ganho > 0 or desconto > 0:
                            add_transacao(competencia_pagina, codigo, desc, ganho, desconto)
                            transacoes_encontradas = True
            
            # ── Fallback: extração por texto se não encontrou tabelas ────
            if not transacoes_encontradas:
                lines = page_text.split("\n")
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Padrão: CÓDIGO DESCRIÇÃO ... VALORES
                    code_m = re.match(r"^(\d+\s*-?\s*\d*)\s+(.+)$", line)
                    if not code_m:
                        continue
                    
                    codigo = code_m.group(1).replace(" ", "")
                    rest = code_m.group(2)
                    
                    values = VALUE_RE.findall(rest)
                    if not values:
                        continue
                    
                    # Remover valores para obter descrição
                    desc = rest
                    for v in values:
                        desc = desc.replace(v, "").strip()
                    desc = re.sub(r"\s+[PV]\s*$", "", desc)
                    desc = re.sub(r"\s+\d+/\d+\s*", " ", desc)
                    desc = re.sub(r"\s+", " ", desc).strip()
                    
                    if not desc or len(desc) < 2:
                        continue
                    
                    ganho = 0.0
                    desconto = 0.0
                    
                    if len(values) >= 2:
                        try:
                            ganho = _parse_currency(values[-2])
                            desconto = _parse_currency(values[-1])
                        except (ValueError, IndexError):
                            pass
                    elif len(values) == 1:
                        try:
                            val = _parse_currency(values[0])
                            if any(kw in desc.upper() for kw in ["BANCO", "EMPRESTIMO", "CONSIG", "CARTAO", "PREVIDENCIA", "INSS"]):
                                desconto = val
                            else:
                                ganho = val
                        except ValueError:
                            pass
                    
                    if ganho > 0 or desconto > 0:
                        add_transacao(competencia_pagina, codigo, desc, ganho, desconto)
    
    # ── Definir período de competência ────────────────────
    if todas_competencias:
        todas_competencias.sort(key=lambda x: (int(x.split("/")[1]), int(x.split("/")[0])))
        if len(todas_competencias) == 1:
            data.competencia = todas_competencias[0]
        else:
            data.competencia = f"{todas_competencias[0]} a {todas_competencias[-1]}"
        
        logger.info("Período processado: %s (%d competências)", data.competencia, len(todas_competencias))
    
    # Calcular totais
    total_ganhos = sum(t.valor for t in data.transacoes if t.tipo == "credito")
    total_descontos = sum(t.valor for t in data.transacoes if t.tipo == "debito")
    data.valor_bruto = total_ganhos
    data.valor_liquido = total_ganhos - total_descontos
    
    logger.info("Contracheque AmazonPrev processado: %d transações (%d ganhos, %d descontos) em %d páginas",
                len(data.transacoes),
                sum(1 for t in data.transacoes if t.tipo == "credito"),
                sum(1 for t in data.transacoes if t.tipo == "debito"),
                len(todas_competencias))
    
    return data, linhas


def _parse_historico_inss(file_bytes: bytes, progress_callback=None) -> tuple[ExtractedData, list[dict]]:
    """
    Parser específico para Histórico de Créditos do INSS.
    
    Formato do documento:
    - Cabeçalho: INSS - INSTITUTO NACIONAL DO SEGURO SOCIAL - Histórico de Créditos
    - Identificação do Filiado: NIT, CPF, Nome, Data de Nascimento
    - Compet. Inicial / Compet. Final no cabeçalho
    - Blocos por competência:
      - Linha: "MM/AAAA  DD/MM/AAAA a DD/MM/AAAA  R$ XXX,XX  Pago  ..."
      - Informações do banco
      - Tabela: Rubrica | Descrição Rubrica | Valor
    
    Suporta lotes de até 10 anos de histórico.
    """
    data = ExtractedData()
    linhas: list[dict] = []
    
    VALUE_RE = re.compile(r"R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})")
    # Padrão para linha de competência: "01/2023  01/01/2023"
    COMP_LINE_RE = re.compile(r"^(\d{1,2}/\d{4})\s+(\d{2}/\d{2}/\d{4})")
    # Padrão para rubrica: "101  VALOR TOTAL DE MR DO PERIODO  R$ 1.302,00"
    RUBRICA_RE = re.compile(r"^\s*(\d{1,4})\s+(.+?)\s+R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*$")
    
    processed_keys = set()
    todas_competencias = []
    
    def normalize_competencia(comp: str) -> str:
        """Normaliza formato: 1/2023 -> 01/2023"""
        parts = comp.split("/")
        if len(parts) == 2:
            mes = parts[0].zfill(2)
            ano = parts[1]
            return f"{mes}/{ano}"
        return comp
    
    def competencia_to_data(comp: str) -> str:
        """
        Converte competência MM/AAAA para data DD/MM/AAAA (último dia do mês).
        Isso é necessário para compatibilidade com os Apêndices que esperam datas completas.
        """
        parts = comp.split("/")
        if len(parts) == 2:
            mes = int(parts[0])
            ano = int(parts[1])
            # Calcular último dia do mês
            if mes == 12:
                ultimo_dia = 31
            else:
                from datetime import date, timedelta
                proximo_mes = date(ano, mes + 1, 1)
                ultimo_dia = (proximo_mes - timedelta(days=1)).day
            return f"{ultimo_dia:02d}/{mes:02d}/{ano}"
        return comp
    
    def add_transacao(competencia: str, codigo: str, desc: str, valor: float):
        """Adiciona transação do histórico INSS"""
        # Converter competência para data completa
        data_completa = competencia_to_data(competencia)
        
        key = f"{competencia}|{codigo}|{desc}|{valor}"
        if key in processed_keys or valor == 0:
            return
        processed_keys.add(key)
        
        # No histórico INSS:
        # - Rubricas 101, 137 são créditos (valor total, adiantamento)
        # - Demais são descontos (consignações, empréstimos)
        is_credito = codigo in ("101", "137") or any(kw in desc.upper() for kw in [
            "VALOR TOTAL", "MR DO PERIODO", "ADIANTAMENTO P/ARREDONDAMENTO"
        ])
        
        tipo = "credito" if is_credito else "debito"
        
        linhas.append({
            "data": data_completa,
            "descricao": f"[{codigo}] {desc}",
            "debito": 0.0 if is_credito else valor,
            "credito": valor if is_credito else 0.0,
            "tipo": tipo,
            "competencia": competencia,  # Manter competência original para referência
        })
        data.transacoes.append(Transacao(
            data=data_completa,
            descricao=f"[{codigo}] {desc}",
            valor=valor,
            tipo=tipo
        ))
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        logger.info("Processando %d páginas de Histórico INSS", len(pdf.pages))
        
        # Concatenar texto de todas as páginas para processamento
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"
        
        # ── Extrair dados de identificação ────────────────────
        # Nome
        nome_m = re.search(r"Nome[:\s]*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]{5,60})", full_text, re.IGNORECASE)
        if nome_m:
            data.nome = nome_m.group(1).strip()
        
        # CPF
        cpf_m = re.search(r"CPF[:\s]*([\d]{3}\.[\d]{3}\.[\d]{3}-[\d]{2})", full_text)
        if cpf_m:
            data.cpf = cpf_m.group(1).strip()
        
        # NIT (matrícula)
        nit_m = re.search(r"NIT[:\s]*([\d\.\-]+)", full_text)
        if nit_m:
            data.matricula = nit_m.group(1).strip()
        
        # Órgão
        data.orgao = "INSS"
        
        # ── Processar linha por linha ────────────────────────
        lines = full_text.split("\n")
        competencia_atual = None
        
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Verificar se é linha de competência
            # Formato: "01/2023  01/01/2023 a 31/01/2023  R$ 773,00  Pago..."
            comp_match = COMP_LINE_RE.match(line)
            if comp_match:
                nova_comp = normalize_competencia(comp_match.group(1))
                if nova_comp != competencia_atual:
                    competencia_atual = nova_comp
                    if competencia_atual not in todas_competencias:
                        todas_competencias.append(competencia_atual)
                    logger.info("Competência encontrada: %s", competencia_atual)
                continue
            
            # Verificar se é linha de rubrica
            # Formato: "101  VALOR TOTAL DE MR DO PERIODO  R$ 1.302,00"
            rubrica_match = RUBRICA_RE.match(line)
            if rubrica_match and competencia_atual:
                codigo = rubrica_match.group(1)
                desc = rubrica_match.group(2).strip()
                valor_str = rubrica_match.group(3)
                
                try:
                    valor = _parse_currency(valor_str)
                    if valor > 0:
                        add_transacao(competencia_atual, codigo, desc, valor)
                except ValueError:
                    pass
                continue
            
            # Fallback: tentar extrair rubrica com formato mais flexível
            # Algumas linhas podem ter espaçamento diferente
            if competencia_atual and re.match(r"^\s*\d{1,4}\s+", line):
                # Extrair código no início
                code_m = re.match(r"^\s*(\d{1,4})\s+(.+)$", line)
                if code_m:
                    codigo = code_m.group(1)
                    resto = code_m.group(2)
                    
                    # Procurar valor no final
                    valores = VALUE_RE.findall(resto)
                    if valores:
                        # Último valor é o valor da rubrica
                        valor_str = valores[-1]
                        # Descrição é o que sobra
                        desc = resto
                        for v in valores:
                            desc = desc.replace(f"R$ {v}", "").replace(v, "")
                        desc = re.sub(r"\s+", " ", desc).strip()
                        
                        if desc and len(desc) >= 3:
                            try:
                                valor = _parse_currency(valor_str)
                                if valor > 0:
                                    add_transacao(competencia_atual, codigo, desc, valor)
                            except ValueError:
                                pass
    
    # ── Definir período de competência ────────────────────
    if todas_competencias:
        todas_competencias.sort(key=lambda x: (int(x.split("/")[1]), int(x.split("/")[0])))
        if len(todas_competencias) == 1:
            data.competencia = todas_competencias[0]
        else:
            data.competencia = f"{todas_competencias[0]} a {todas_competencias[-1]}"
        
        logger.info("Período processado: %s (%d competências)", data.competencia, len(todas_competencias))
    
    # Calcular totais
    total_creditos = sum(t.valor for t in data.transacoes if t.tipo == "credito")
    total_debitos = sum(t.valor for t in data.transacoes if t.tipo == "debito")
    data.valor_bruto = total_creditos
    data.valor_liquido = total_creditos - total_debitos
    
    logger.info("Histórico INSS processado: %d transações (%d créditos, %d débitos) em %d competências",
                len(data.transacoes),
                sum(1 for t in data.transacoes if t.tipo == "credito"),
                sum(1 for t in data.transacoes if t.tipo == "debito"),
                len(todas_competencias))
    
    return data, linhas


def _parse_contracheque_semad(file_bytes: bytes, progress_callback=None) -> tuple[ExtractedData, list[dict]]:
    """
    Parser para Contracheque SEMAD/Prefeitura de Manaus e PMM AM.
    
    Formato:
    - Cabeçalho: ÓRGÃO, DESCRIÇÃO LOTAÇÃO, MATRÍCULA SEQ-DIG
    - NOME, Nº REGISTRO GERAL, UF, ÓRG. EMISSOR
    - DATA (competência MM/AAAA), BANCO, AGÊNCIA, CONTA-DV, SALÁRIO
    - Tabela: COD | DESCRIÇÃO | PARC | INF. | BASE | GANHOS | DESCONTOS
    - Totais: TOTAL DE GANHOS (P+V) | TOTAL DE DESCONTOS (D) | LÍQUIDO | FGTS
    
    IMPORTANTE: A data de saída é formatada como DD/MM/AAAA (último dia do mês)
    para compatibilidade com os Apêndices.
    """
    data = ExtractedData()
    linhas: list[dict] = []
    
    VALUE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")
    DATE_MM_YYYY = re.compile(r"\b(\d{1,2}/\d{4})\b")
    
    processed_keys = set()
    todas_competencias = []
    
    def normalize_competencia(comp: str) -> str:
        """Normaliza MM/AAAA para 0M/AAAA"""
        parts = comp.split("/")
        if len(parts) == 2:
            return f"{parts[0].zfill(2)}/{parts[1]}"
        return comp
    
    def competencia_to_data(comp: str) -> str:
        """
        Converte competência MM/AAAA para data DD/MM/AAAA (último dia do mês).
        Isso é necessário para compatibilidade com os Apêndices que esperam datas completas.
        """
        parts = comp.split("/")
        if len(parts) == 2:
            mes = int(parts[0])
            ano = int(parts[1])
            # Calcular último dia do mês
            if mes == 12:
                ultimo_dia = 31
            else:
                from datetime import date
                proximo_mes = date(ano, mes + 1, 1)
                ultimo_dia = (proximo_mes - __import__('datetime').timedelta(days=1)).day
            return f"{ultimo_dia:02d}/{mes:02d}/{ano}"
        return comp
    
    def add_transacao(competencia: str, codigo: str, desc: str, ganho: float, desconto: float):
        """Adiciona transação com data formatada como DD/MM/AAAA"""
        # Converter competência para data completa
        data_completa = competencia_to_data(competencia)
        
        key = f"{competencia}|{codigo}|{desc}|{ganho}|{desconto}"
        if key in processed_keys:
            return
        processed_keys.add(key)
        
        if desconto > 0:
            linhas.append({
                "data": data_completa,
                "descricao": f"[{codigo}] {desc}",
                "debito": desconto,
                "credito": 0.0,
                "tipo": "debito",
                "competencia": competencia,  # Manter competência original para referência
            })
            data.transacoes.append(Transacao(
                data=data_completa,
                descricao=f"[{codigo}] {desc}",
                valor=desconto,
                tipo="debito"
            ))
        if ganho > 0:
            linhas.append({
                "data": data_completa,
                "descricao": f"[{codigo}] {desc}",
                "debito": 0.0,
                "credito": ganho,
                "tipo": "credito",
                "competencia": competencia,
            })
            data.transacoes.append(Transacao(
                data=data_completa,
                descricao=f"[{codigo}] {desc}",
                valor=ganho,
                tipo="credito"
            ))
    
    def report_progress(progress: int, message: str, current_page: int = 0, total_pages: int = 0):
        if progress_callback:
            progress_callback(progress, message, current_page, total_pages)
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        total_pages = len(pdf.pages)
        logger.info("Processando %d páginas de Contracheque SEMAD/PMM", total_pages)
        report_progress(15, f"Processando {total_pages} páginas...", 0, total_pages)
        
        cliente_extraido = False
        
        for page_idx, page in enumerate(pdf.pages):
            if page_idx % 10 == 0:
                progress = 15 + int((page_idx / total_pages) * 75)
                report_progress(progress, f"Página {page_idx + 1} de {total_pages}", page_idx + 1, total_pages)
            
            page_text = page.extract_text() or ""
            lines = page_text.split("\n")
            
            # ── Extrair competência da página ────────────────
            competencia_pagina = None
            for line in lines[:15]:
                # Formato: "11/2014  237  000320  00696061-8  ..."
                dates = DATE_MM_YYYY.findall(line)
                for d in dates:
                    parts = d.split("/")
                    if len(parts) == 2:
                        try:
                            mes, ano = int(parts[0]), int(parts[1])
                            if 1 <= mes <= 12 and 2000 <= ano <= 2030:
                                competencia_pagina = normalize_competencia(d)
                                break
                        except ValueError:
                            continue
                if competencia_pagina:
                    break
            
            if not competencia_pagina:
                competencia_pagina = todas_competencias[-1] if todas_competencias else "01/2024"
            else:
                if competencia_pagina not in todas_competencias:
                    todas_competencias.append(competencia_pagina)
            
            # ── Extrair dados pessoais (primeira página) ─────
            if not cliente_extraido:
                for i, line in enumerate(lines):
                    upper_line = line.upper().strip()
                    # Nome: linha após "NOME"
                    if "NOME" in upper_line and "REGISTRO" in upper_line:
                        if i + 1 < len(lines):
                            nome_line = lines[i + 1].strip()
                            nome_m = re.match(r"([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]+?)(?:\s+\d)", nome_line)
                            if nome_m:
                                data.nome = nome_m.group(1).strip()
                    # Órgão
                    if "ÓRGÃO" in upper_line or "ORGAO" in upper_line:
                        if i + 1 < len(lines):
                            orgao_line = lines[i + 1].strip()
                            orgao_m = re.match(r"([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]+?)(?:\s{2,})", orgao_line)
                            if orgao_m:
                                data.orgao = orgao_m.group(1).strip()
                    # Matrícula
                    if "MATRÍCULA" in upper_line or "MATRICULA" in upper_line:
                        if i + 1 < len(lines):
                            mat_line = lines[i + 1].strip()
                            mat_m = re.search(r"(\d[\d\.\-]+\s*[A-Z]?)", mat_line)
                            if mat_m:
                                data.matricula = mat_m.group(1).strip()
                
                if data.nome:
                    cliente_extraido = True
            
            # ── Extrair rubricas via tabelas (mais preciso) ──
            tables = page.extract_tables()
            rubricas_encontradas = False
            
            for table in tables:
                if not table:
                    continue
                
                # Detectar cabeçalho da tabela de rubricas
                header_row = -1
                codigo_col = -1
                desc_col = -1
                ganhos_col = -1
                descontos_col = -1
                
                for row_idx, row in enumerate(table):
                    if not row:
                        continue
                    cells = [str(c).strip().upper() if c else "" for c in row]
                    
                    for col_idx, cell in enumerate(cells):
                        if "COD" in cell or "CÓDIGO" in cell:
                            codigo_col = col_idx
                            header_row = row_idx
                        elif "DESCRIÇÃO" in cell or "DESCRICAO" in cell:
                            desc_col = col_idx
                        elif "GANHOS" in cell:
                            ganhos_col = col_idx
                        elif "DESCONTOS" in cell:
                            descontos_col = col_idx
                
                if header_row < 0 or codigo_col < 0:
                    continue
                
                # Processar linhas de dados
                for row_idx, row in enumerate(table):
                    if row_idx <= header_row or not row:
                        continue
                    
                    cells = [str(c).strip() if c else "" for c in row]
                    
                    # Extrair código
                    codigo_cell = cells[codigo_col] if codigo_col < len(cells) else ""
                    if not codigo_cell or not re.match(r"^\d{1,6}$", codigo_cell.replace(" ", "")):
                        continue
                    codigo = codigo_cell.replace(" ", "")
                    
                    # Extrair descrição
                    desc = cells[desc_col] if desc_col >= 0 and desc_col < len(cells) else ""
                    if not desc or len(desc) < 2:
                        continue
                    desc = re.sub(r"\s+", " ", desc).strip()
                    
                    # Extrair ganhos
                    ganho = 0.0
                    if ganhos_col >= 0 and ganhos_col < len(cells):
                        ganho_str = cells[ganhos_col]
                        vm = VALUE_RE.search(ganho_str)
                        if vm:
                            try:
                                ganho = _parse_currency(vm.group(1))
                            except ValueError:
                                pass
                    
                    # Extrair descontos
                    desconto = 0.0
                    if descontos_col >= 0 and descontos_col < len(cells):
                        desc_str = cells[descontos_col]
                        vm = VALUE_RE.search(desc_str)
                        if vm:
                            try:
                                desconto = _parse_currency(vm.group(1))
                            except ValueError:
                                pass
                    
                    if ganho > 0 or desconto > 0:
                        add_transacao(competencia_pagina, codigo, desc, ganho, desconto)
                        rubricas_encontradas = True
            
            # ── Fallback: extração por texto se não encontrou tabelas ──
            if not rubricas_encontradas:
                in_rubricas = False
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    upper_line = line.upper()
                    
                    # Detectar início da tabela de rubricas
                    if ("COD" in upper_line or "CÓDIGO" in upper_line) and \
                       ("DESCRIÇÃO" in upper_line or "DESCRICAO" in upper_line) and \
                       ("GANHOS" in upper_line or "DESCONTOS" in upper_line):
                        in_rubricas = True
                        continue
                    
                    # Detectar fim da tabela
                    if "TOTAL DE GANHOS" in upper_line or "TOTAL DE DESCONTOS" in upper_line:
                        in_rubricas = False
                        continue
                    
                    if not in_rubricas:
                        continue
                    
                    # Extrair rubrica: COD  DESCRIÇÃO  PARC  INF  BASE  GANHOS  DESCONTOS
                    code_m = re.match(r"^(\d{1,6})\s+", line)
                    if not code_m:
                        continue
                    
                    codigo = code_m.group(1)
                    after_code = line[len(code_m.group(0)):]
                    
                    # Extrair valores monetários
                    values = VALUE_RE.findall(after_code)
                    if not values:
                        continue
                    
                    # Descrição é o texto antes do primeiro valor
                    first_val_idx = after_code.index(values[0])
                    desc = after_code[:first_val_idx].strip()
                    desc = re.sub(r"\s+[PVDGHQ]\s*$", "", desc).strip()
                    
                    if not desc or len(desc) < 2:
                        continue
                    
                    # Determinar ganhos e descontos
                    ganho = 0.0
                    desconto = 0.0
                    
                    parsed_vals = [_parse_currency(v) for v in values]
                    
                    if len(parsed_vals) >= 2:
                        ganho = parsed_vals[-2]
                        desconto = parsed_vals[-1]
                    elif len(parsed_vals) == 1:
                        is_desconto = int(codigo) >= 5000 or any(kw in desc.upper() for kw in [
                            "INSS", "IRRF", "IMPOSTO", "CONSIG", "PREV", "CARTAO", "EMPRESTIMO",
                            "DESCONTO", "PENSAO", "BRADESCO", "BONSUCESSO", "MANAUS", "MANAUSPREV"
                        ])
                        if is_desconto:
                            desconto = parsed_vals[0]
                        else:
                            ganho = parsed_vals[0]
                    
                    if ganho > 0 or desconto > 0:
                        add_transacao(competencia_pagina, codigo, desc, ganho, desconto)
    
    # Definir período
    if todas_competencias:
        todas_competencias.sort(key=lambda x: (int(x.split("/")[1]), int(x.split("/")[0])))
        data.competencia = f"{todas_competencias[0]} a {todas_competencias[-1]}" if len(todas_competencias) > 1 else todas_competencias[0]
    
    if not data.orgao:
        data.orgao = "SEMAD/Prefeitura de Manaus"
    
    total_ganhos = sum(t.valor for t in data.transacoes if t.tipo == "credito")
    total_descontos = sum(t.valor for t in data.transacoes if t.tipo == "debito")
    data.valor_bruto = total_ganhos
    data.valor_liquido = total_ganhos - total_descontos
    
    report_progress(90, f"Processadas {len(data.transacoes)} transações em {len(todas_competencias)} competências")
    logger.info("Contracheque SEMAD/PMM: %d transações em %d competências", len(data.transacoes), len(todas_competencias))
    
    return data, linhas


def _parse_fatura_ole_santander(file_bytes: bytes, progress_callback=None) -> tuple[ExtractedData, list[dict]]:
    """
    Parser específico para Fatura de Cartão Consignado Olé-Santander.
    
    Formato do documento (texto corrido):
    - Linha de cabeçalho do cliente: CONTA CPF CLIENTE VCTO CARTAO ...
    - Linha de dados do cliente: 0004027029240423541 57314683204 NOME 09/03/2012 ***3541 0 0 0
    - Linhas de transação: DD/MM DESCRIÇÃO DEBITO CREDITO TOTAL
    - Linhas de resumo: TOTAL DA FATURA, MINIMO DA FATURA, ENCARGOS, JUROS % AM
    
    Otimizado para processar documentos grandes (500+ páginas).
    """
    data = ExtractedData()
    linhas: list[dict] = []
    
    def report_progress(progress: int, message: str, current_page: int = 0, total_pages: int = 0):
        if progress_callback:
            progress_callback(progress, message, current_page, total_pages)
    
    # Regex compilados uma única vez
    VALUE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{1,2}|\d+,\d{1,2})")
    DATE_DD_MM = re.compile(r"^(\d{2}/\d{2})\s+")
    CLIENTE_LINE_RE = re.compile(
        r"^(\d{19})\s+(\d{11})\s+([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]+?)\s+(\d{2}/\d{2}/\d{4})\s+"
    )
    
    processed_keys = set()
    todas_competencias = []
    
    DESCRICOES_RESUMO = {"TOTAL DA FATURA", "MINIMO DA FATURA", "ENCARGOS", "JUROS % AM", "JUROS %AM"}
    
    def parse_valor(val_str: str) -> float:
        if not val_str:
            return 0.0
        try:
            return float(val_str.replace(".", "").replace(",", "."))
        except ValueError:
            return 0.0
    
    competencia_atual = None
    cliente_extraido = False
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        total_pages = len(pdf.pages)
        logger.info("Iniciando processamento de %d páginas de Fatura Olé-Santander", total_pages)
        report_progress(15, f"Processando {total_pages} páginas...", 0, total_pages)
        
        for page_idx, page in enumerate(pdf.pages):
            # Atualizar progresso a cada 10 páginas ou no início
            if page_idx % 10 == 0 or page_idx == 0:
                progress = 15 + int((page_idx / total_pages) * 75)  # 15-90%
                report_progress(progress, f"Página {page_idx + 1} de {total_pages}", page_idx + 1, total_pages)
            
            # Log de progresso a cada 50 páginas
            if page_idx % 50 == 0:
                logger.info("Processando página %d/%d (%.1f%%)", page_idx + 1, total_pages, (page_idx / total_pages) * 100)
            
            page_text = page.extract_text() or ""
            
            for line in page_text.split("\n"):
                line = line.strip()
                if not line or len(line) < 5 or line.startswith("CONTA CPF"):
                    continue
                
                # Detectar linha de cliente (nova competência)
                cliente_match = CLIENTE_LINE_RE.match(line)
                if cliente_match:
                    if not cliente_extraido:
                        cpf_raw = cliente_match.group(2)
                        data.matricula = cliente_match.group(1)
                        data.cpf = f"{cpf_raw[:3]}.{cpf_raw[3:6]}.{cpf_raw[6:9]}-{cpf_raw[9:]}"
                        data.nome = cliente_match.group(3).strip()
                        data.orgao = "Olé Consignado - Santander"
                        cliente_extraido = True
                    
                    vcto = cliente_match.group(4)
                    parts = vcto.split("/")
                    if len(parts) == 3:
                        nova_comp = f"{parts[1]}/{parts[2]}"
                        if nova_comp != competencia_atual:
                            competencia_atual = nova_comp
                            if competencia_atual not in todas_competencias:
                                todas_competencias.append(competencia_atual)
                    continue
                
                # Detectar transação (DD/MM DESCRIÇÃO VALORES)
                dt_match = DATE_DD_MM.match(line)
                if dt_match and competencia_atual:
                    data_mov = dt_match.group(1)
                    resto = line[len(dt_match.group(0)):].strip()
                    
                    # Extrair os 3 valores numéricos da linha (DEBITO, CREDITO, TOTAL)
                    # O formato é: DESCRIÇÃO  DEBITO  CREDITO  TOTAL
                    # Valores podem ser "0" ou "1.234,56"
                    # Usar regex que captura tanto zeros quanto valores monetários
                    ALL_VALUES_RE = re.compile(r"(?:^|\s)(0|(?:\d{1,3}(?:\.\d{3})*,\d{1,2}))(?=\s|$)")
                    all_vals = ALL_VALUES_RE.findall(resto)
                    
                    # Precisamos de pelo menos 2 valores (débito + crédito) ou 3 (débito + crédito + total)
                    if len(all_vals) >= 2:
                        # Extrair descrição removendo os valores do final
                        desc = resto
                        # Remover valores do final da string
                        for v in reversed(all_vals):
                            last_pos = desc.rfind(v)
                            if last_pos >= 0:
                                desc = desc[:last_pos] + desc[last_pos + len(v):]
                        desc = re.sub(r"\s+", " ", desc).strip()
                        
                        if desc and len(desc) >= 3 and desc.upper() not in DESCRICOES_RESUMO:
                            # Pegar os últimos 2 ou 3 valores como débito/crédito/total
                            # Se tiver 3+: últimos 3 = débito, crédito, total
                            # Se tiver 2: débito, crédito
                            if len(all_vals) >= 3:
                                debito = parse_valor(all_vals[-3])
                                credito = parse_valor(all_vals[-2])
                            else:
                                debito = parse_valor(all_vals[-2])
                                credito = parse_valor(all_vals[-1])
                            
                            # REGRA FATURA CONSIGNADO: "PAGAMENTO EFETUADO" e "DESCONTO EM FOLHA"
                            # aparecem na coluna crédito do PDF, mas são DÉBITOS do servidor
                            # (valores descontados do servidor público para pagar a fatura)
                            desc_upper = desc.upper()
                            if credito > 0 and debito == 0 and (
                                "PAGAMENTO" in desc_upper or "DESCONTO" in desc_upper
                            ):
                                debito = credito
                                credito = 0.0
                            
                            if debito > 0 or credito > 0:
                                key = f"{competencia_atual}|{data_mov}|{desc}|{debito}|{credito}"
                                if key not in processed_keys:
                                    processed_keys.add(key)
                                    ano = competencia_atual.split("/")[1] if "/" in competencia_atual else "2012"
                                    data_completa = f"{data_mov}/{ano}"
                                    
                                    if debito > 0:
                                        linhas.append({"data": data_completa, "descricao": desc, "debito": debito, "credito": 0.0, "tipo": "debito", "competencia": competencia_atual})
                                        data.transacoes.append(Transacao(data=data_completa, descricao=desc, valor=debito, tipo="debito"))
                                    if credito > 0:
                                        linhas.append({"data": data_completa, "descricao": desc, "debito": 0.0, "credito": credito, "tipo": "credito", "competencia": competencia_atual})
                                        data.transacoes.append(Transacao(data=data_completa, descricao=desc, valor=credito, tipo="credito"))
    
    # Definir período
    if todas_competencias:
        todas_competencias.sort(key=lambda x: (int(x.split("/")[1]), int(x.split("/")[0])))
        data.competencia = f"{todas_competencias[0]} a {todas_competencias[-1]}" if len(todas_competencias) > 1 else todas_competencias[0]
    
    # Totais
    data.valor_bruto = sum(t.valor for t in data.transacoes if t.tipo == "credito")
    data.valor_liquido = data.valor_bruto - sum(t.valor for t in data.transacoes if t.tipo == "debito")
    
    report_progress(90, f"Processadas {len(data.transacoes)} transações em {len(todas_competencias)} competências")
    logger.info("Fatura Olé-Santander: %d transações em %d competências", len(data.transacoes), len(todas_competencias))
    
    return data, linhas


def _parse_ficha_financeira_sead(file_bytes: bytes, progress_callback=None) -> tuple[ExtractedData, list[dict]]:
    """
    Parser para Ficha Financeira SEAD (Secretaria de Estado de Administração e Gestão - AM).
    
    Formato:
    - Cabeçalho: ESTADO DO AMAZONAS / SEAD / FICHA FINANCEIRA - PERIODO JAN/AAAA A DEZ/AAAA
    - Dados: Órgão, Lotação, Servidor (matrícula + nome)
    - Blocos por competência: "- ABRIL/2016", "- MAIO/2016"
    - Sub-bloco: "10  FOLHA MENSAL"
    - Tabela: COD DESCRICAO  +- BASE-+  INF  +-- GANHO --+  +- DESCONTO -+
    - Totais: LIQUIDO:  X.XXX,XX   GANHO   DESCONTO
    """
    data = ExtractedData()
    linhas: list[dict] = []
    
    VALUE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")
    
    MESES = {
        "JANEIRO": "01", "FEVEREIRO": "02", "MARCO": "03", "MARÇO": "03",
        "ABRIL": "04", "MAIO": "05", "JUNHO": "06",
        "JULHO": "07", "AGOSTO": "08", "SETEMBRO": "09",
        "OUTUBRO": "10", "NOVEMBRO": "11", "DEZEMBRO": "12",
    }
    
    processed_keys = set()
    todas_competencias = []
    
    def mes_nome_to_num(nome: str) -> str:
        return MESES.get(nome.upper().strip(), "01")
    
    def competencia_to_data(comp: str) -> str:
        parts = comp.split("/")
        if len(parts) == 2:
            mes = int(parts[0])
            ano = int(parts[1])
            if mes == 12:
                ultimo_dia = 31
            else:
                from datetime import date, timedelta
                proximo_mes = date(ano, mes + 1, 1)
                ultimo_dia = (proximo_mes - timedelta(days=1)).day
            return f"{ultimo_dia:02d}/{mes:02d}/{ano}"
        return comp
    
    def add_transacao(competencia: str, codigo: str, desc: str, ganho: float, desconto: float):
        data_completa = competencia_to_data(competencia)
        key = f"{competencia}|{codigo}|{desc}|{ganho}|{desconto}"
        if key in processed_keys:
            return
        processed_keys.add(key)
        
        if desconto > 0:
            linhas.append({
                "data": data_completa,
                "descricao": f"[{codigo}] {desc}",
                "debito": desconto,
                "credito": 0.0,
                "tipo": "debito",
                "competencia": competencia,
            })
            data.transacoes.append(Transacao(
                data=data_completa, descricao=f"[{codigo}] {desc}",
                valor=desconto, tipo="debito"
            ))
        if ganho > 0:
            linhas.append({
                "data": data_completa,
                "descricao": f"[{codigo}] {desc}",
                "debito": 0.0,
                "credito": ganho,
                "tipo": "credito",
                "competencia": competencia,
            })
            data.transacoes.append(Transacao(
                data=data_completa, descricao=f"[{codigo}] {desc}",
                valor=ganho, tipo="credito"
            ))
    
    def report_progress(progress: int, message: str, current_page: int = 0, total_pages: int = 0):
        if progress_callback:
            progress_callback(progress, message, current_page, total_pages)
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        total_pages = len(pdf.pages)
        logger.info("Processando %d páginas de Ficha Financeira SEAD", total_pages)
        report_progress(15, f"Processando {total_pages} páginas...", 0, total_pages)
        
        # Concatenar texto de todas as páginas
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"
        
        # ── Extrair dados pessoais do cabeçalho ──────────────
        # Servidor: "053.267-3 B - CARLOS ALBERTO PEREIRA DA SILVA"
        servidor_m = re.search(
            r"Servidor\s*\n?\s*([\d\.\-]+\s*[A-Z]?)\s*[-–]\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)",
            full_text, re.IGNORECASE
        )
        if servidor_m:
            data.matricula = servidor_m.group(1).strip()
            data.nome = servidor_m.group(2).strip()
        
        # Órgão
        orgao_m = re.search(r"[ÓO]rg[ãa]o\s*\n?\s*(\d+\s*[-–]\s*[^\n]+)", full_text, re.IGNORECASE)
        if orgao_m:
            data.orgao = orgao_m.group(1).strip()
        
        if not data.orgao:
            data.orgao = "SEAD/Governo do Amazonas"
        
        # ── Processar linha por linha ────────────────────────
        lines = full_text.split("\n")
        competencia_atual = None
        in_tabela = False
        
        for line_idx, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            upper_line = line_stripped.upper()
            
            # Detectar competência: "- ABRIL/2016" ou "- MAIO/2016"
            comp_match = re.match(r"^[-–]\s+([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]+)/(\d{4})\s*$", line_stripped)
            if comp_match:
                mes_nome = comp_match.group(1)
                ano = comp_match.group(2)
                mes_num = mes_nome_to_num(mes_nome)
                competencia_atual = f"{mes_num}/{ano}"
                if competencia_atual not in todas_competencias:
                    todas_competencias.append(competencia_atual)
                in_tabela = False
                continue
            
            # Detectar cabeçalho da tabela
            if "COD" in upper_line and "DESCRICAO" in upper_line and ("GANHO" in upper_line or "DESCONTO" in upper_line):
                in_tabela = True
                continue
            
            # Detectar sub-bloco "10  FOLHA MENSAL" — manter in_tabela
            if re.match(r"^\d{1,2}\s+FOLHA\s+MENSAL", upper_line):
                continue
            
            # Detectar fim: LIQUIDO
            if "LIQUIDO:" in upper_line:
                in_tabela = False
                continue
            
            # Se não estamos em tabela ou sem competência, pular
            if not in_tabela or not competencia_atual:
                continue
            
            # Extrair rubrica: COD DESCRICAO  BASE  *  GANHO  DESCONTO
            # Formato: "0059 ETAPAS           30,00     *          75,00"
            # ou:      "5253 IMPOSTO DE RENDA  7,50     *                    45,87"
            code_m = re.match(r"^(\d{4})\s+(.+)$", line_stripped)
            if not code_m:
                continue
            
            codigo = code_m.group(1)
            resto = code_m.group(2)
            
            # Extrair todos os valores monetários
            values = VALUE_RE.findall(resto)
            if not values:
                continue
            
            # Descrição: texto antes do primeiro valor
            first_val_pos = resto.index(values[0])
            desc = resto[:first_val_pos].strip()
            # Limpar descrição
            desc = re.sub(r"\s+", " ", desc).strip()
            if not desc or len(desc) < 2:
                continue
            
            # Determinar ganho e desconto
            # Na ficha SEAD, o formato é: BASE  *  GANHO  DESCONTO
            # Pode ter 1, 2 ou 3 valores
            ganho = 0.0
            desconto = 0.0
            
            parsed_vals = [_parse_currency(v) for v in values]
            
            if len(parsed_vals) >= 3:
                # BASE, GANHO, DESCONTO
                ganho = parsed_vals[-2]
                desconto = parsed_vals[-1]
            elif len(parsed_vals) == 2:
                # BASE + GANHO ou BASE + DESCONTO
                # Verificar posição no texto para determinar
                # Se o segundo valor está mais à direita, é desconto
                val1_pos = resto.index(values[0])
                val2_pos = resto.index(values[1], val1_pos + len(values[0]))
                
                # Heurística: se o código >= 5000 ou contém keywords de desconto
                is_desconto = int(codigo) >= 5000 or any(kw in desc.upper() for kw in [
                    "IMPOSTO", "INSS", "IRRF", "CONSIG", "PREV", "CARTAO", "EMPRESTIMO",
                    "DESCONTO", "PENSAO", "BRADESCO", "BONSUCESSO", "BMG", "BMC", "BIB",
                    "BANCO", "VOTORANTIM", "OLE", "AMAZONPREV", "RETORNO", "MANAUSPREV"
                ])
                
                if is_desconto:
                    desconto = parsed_vals[1]
                else:
                    ganho = parsed_vals[1]
            elif len(parsed_vals) == 1:
                is_desconto = int(codigo) >= 5000 or any(kw in desc.upper() for kw in [
                    "IMPOSTO", "INSS", "IRRF", "CONSIG", "PREV", "CARTAO", "EMPRESTIMO",
                    "DESCONTO", "PENSAO", "BRADESCO", "BONSUCESSO", "BMG", "BMC", "BIB",
                    "BANCO", "VOTORANTIM", "OLE", "AMAZONPREV", "RETORNO", "MANAUSPREV"
                ])
                if is_desconto:
                    desconto = parsed_vals[0]
                else:
                    ganho = parsed_vals[0]
            
            if ganho > 0 or desconto > 0:
                add_transacao(competencia_atual, codigo, desc, ganho, desconto)
    
    # Definir período
    if todas_competencias:
        todas_competencias.sort(key=lambda x: (int(x.split("/")[1]), int(x.split("/")[0])))
        data.competencia = f"{todas_competencias[0]} a {todas_competencias[-1]}" if len(todas_competencias) > 1 else todas_competencias[0]
    
    total_ganhos = sum(t.valor for t in data.transacoes if t.tipo == "credito")
    total_descontos = sum(t.valor for t in data.transacoes if t.tipo == "debito")
    data.valor_bruto = total_ganhos
    data.valor_liquido = total_ganhos - total_descontos
    
    report_progress(90, f"Processadas {len(data.transacoes)} transações em {len(todas_competencias)} competências")
    logger.info("Ficha Financeira SEAD: %d transações em %d competências", len(data.transacoes), len(todas_competencias))
    
    return data, linhas


def _parse_extrato_bancario(file_bytes: bytes, progress_callback=None) -> tuple[ExtractedData, list[dict]]:
    """
    Parser específico para extratos bancários Bradesco.
    
    Formato do texto extraído:
    - Linhas com data: DD/MM/YYYY DESCRIÇÃO DOCTO VALOR SALDO
    - Linhas sem data: continuação da descrição ou nova transação
    - Créditos: INSS, SALARIO, DEPOSITO, etc.
    - Débitos: PARCELA, TARIFA, SAQUE, CARTAO, IOF, ENCARGOS, etc.
    """
    data = ExtractedData()
    linhas: list[dict] = []

    # Regex
    DATE_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.*)$")
    VALUE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")
    
    # Keywords para identificar créditos
    CREDITO_KEYWORDS = [
        "INSS", "SALARIO", "SALÁRIO", "DEPOSITO", "DEPÓSITO", "DEP ", 
        "CREDITO EM", "CRÉDITO EM", "TED RECEBIDA", "PIX RECEBIDO",
        "TRANSFERENCIA RECEBIDA", "DEVOLUCAO", "REEMBOLSO", "ESTORNO"
    ]

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

        # ── Cabeçalho ────────────────────────────────────────
        nome_m = re.search(r"Nome[:\s]*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑA-Za-záàâãéèêíïóôõöúçñ\s]{5,60})", full_text)
        if nome_m:
            data.nome = nome_m.group(1).strip()

        agencia_m = re.search(r"Ag[êe]ncia[:\s]*(\d+)", full_text, re.IGNORECASE)
        conta_m = re.search(r"Conta[:\s]*([\d\.\-]+)", full_text, re.IGNORECASE)
        periodo_m = re.search(r"entre[:\s]*(\d{2}/\d{2}/\d{4})\s+e\s+(\d{2}/\d{2}/\d{4})", full_text, re.IGNORECASE)

        if agencia_m and conta_m:
            data.orgao = f"Ag. {agencia_m.group(1)} | Conta {conta_m.group(1)}"
        if periodo_m:
            data.competencia = f"{periodo_m.group(1)} a {periodo_m.group(2)}"

        # ── Extração de transações ────────────────────────────
        processed_keys = set()

        def is_credito(desc: str) -> bool:
            """Verifica se a descrição indica um crédito"""
            desc_upper = desc.upper()
            return any(kw in desc_upper for kw in CREDITO_KEYWORDS)

        def add_transacao(date: str, desc: str, valor: float):
            """Adiciona transação identificando se é débito ou crédito"""
            key = f"{date}|{desc}|{valor}"
            if key in processed_keys or valor == 0:
                return
            processed_keys.add(key)
            
            tipo = "credito" if is_credito(desc) else "debito"
            
            if tipo == "debito":
                linhas.append({
                    "data": date,
                    "descricao": desc,
                    "debito": valor,
                    "credito": 0.0,
                    "tipo": "debito",
                })
                data.transacoes.append(Transacao(
                    data=date, descricao=desc, valor=valor, tipo="debito"
                ))
            else:
                linhas.append({
                    "data": date,
                    "descricao": desc,
                    "debito": 0.0,
                    "credito": valor,
                    "tipo": "credito",
                })
                data.transacoes.append(Transacao(
                    data=date, descricao=desc, valor=valor, tipo="credito"
                ))

        # ── Processar texto linha a linha ────────────────────
        last_date = ""
        pending_desc = ""
        
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Ignorar cabeçalhos e linhas de sistema
                line_upper = line.upper()
                if any(h in line_upper for h in [
                    "HISTÓRICO", "HISTORICO", "CRÉDITO (R$)", "DÉBITO (R$)", 
                    "SALDO (R$)", "DOCTO.", "FOLHA:", "BRADESCO", "CELULAR",
                    "EXTRATO DE:", "MOVIMENTAÇÃO ENTRE", "DATA:"
                ]):
                    continue
                
                # Verificar se a linha começa com data
                date_match = DATE_RE.match(line)
                
                if date_match:
                    # Se tinha transação pendente, processar
                    if pending_desc and last_date:
                        values = VALUE_RE.findall(pending_desc)
                        if values:
                            # Remover valores da descrição
                            desc = pending_desc
                            for v in values:
                                desc = desc.replace(v, "").strip()
                            desc = re.sub(r"\s+", " ", desc).strip()
                            desc = re.sub(r"^\d+\s*", "", desc).strip()  # Remover número do documento
                            
                            if desc and len(desc) >= 3:
                                # Primeiro valor é o movimento (débito ou crédito)
                                valor = _parse_currency(values[0])
                                add_transacao(last_date, desc, valor)
                    
                    # Nova transação
                    last_date = date_match.group(1)
                    pending_desc = date_match.group(2).strip()
                
                elif last_date:
                    # Linha sem data
                    values = VALUE_RE.findall(line)
                    
                    if values:
                        # Linha com valores - pode ser transação ou continuação
                        # Verificar se parece ser uma nova transação (tem descrição antes dos valores)
                        desc_part = line
                        for v in values:
                            desc_part = desc_part.replace(v, "").strip()
                        desc_part = re.sub(r"\s+", " ", desc_part).strip()
                        desc_part = re.sub(r"^\d+\s*", "", desc_part).strip()  # Remover número do documento
                        
                        if desc_part and len(desc_part) >= 3:
                            # É uma nova transação sem data (usa a última data)
                            # Primeiro processar a pendente
                            if pending_desc:
                                pv = VALUE_RE.findall(pending_desc)
                                if pv:
                                    pd = pending_desc
                                    for v in pv:
                                        pd = pd.replace(v, "").strip()
                                    pd = re.sub(r"\s+", " ", pd).strip()
                                    pd = re.sub(r"^\d+\s*", "", pd).strip()
                                    if pd and len(pd) >= 3:
                                        valor = _parse_currency(pv[0])
                                        add_transacao(last_date, pd, valor)
                            
                            # Agora processar a nova
                            valor = _parse_currency(values[0])
                            add_transacao(last_date, desc_part, valor)
                            pending_desc = ""
                        else:
                            # Continuação da descrição anterior
                            if pending_desc:
                                pending_desc = f"{pending_desc} {line}"
                            else:
                                pending_desc = line
                    else:
                        # Linha sem valores - continuação da descrição
                        if pending_desc:
                            pending_desc = f"{pending_desc} {line}"
                        else:
                            pending_desc = line
            
            # Processar última transação pendente da página
            if pending_desc and last_date:
                values = VALUE_RE.findall(pending_desc)
                if values:
                    desc = pending_desc
                    for v in values:
                        desc = desc.replace(v, "").strip()
                    desc = re.sub(r"\s+", " ", desc).strip()
                    desc = re.sub(r"^\d+\s*", "", desc).strip()
                    
                    if desc and len(desc) >= 3:
                        valor = _parse_currency(values[0])
                        add_transacao(last_date, desc, valor)
                pending_desc = ""

    # Calcular totais
    total_debito = sum(t.valor for t in data.transacoes if t.tipo == "debito")
    total_credito = sum(t.valor for t in data.transacoes if t.tipo == "credito")
    data.valor_bruto = total_credito
    data.valor_liquido = total_credito - total_debito

    logger.info("Extrato bancário processado: %d transações (%d débitos, %d créditos)",
                len(data.transacoes),
                sum(1 for t in data.transacoes if t.tipo == "debito"),
                sum(1 for t in data.transacoes if t.tipo == "credito"))

    return data, linhas


def process_pdf(file_bytes: bytes, profile: str = "auto", keywords: list[str] | None = None, progress_callback=None) -> ExtractedData:
    """Main entry point — extract and analyze a PDF document."""
    data = ExtractedData()
    
    def report_progress(progress: int, message: str, current_page: int = 0, total_pages: int = 0):
        if progress_callback:
            progress_callback(progress, message, current_page, total_pages)

    try:
        report_progress(5, "Analisando documento...")
        
        # Extrair texto para detecção automática
        probe_text = _extract_text_pdfplumber(file_bytes).upper()
        
        report_progress(10, "Detectando tipo de documento...")
        
        # ── Fatura Olé-Santander ─────────────────────────────────
        is_fatura_ole = profile == "fatura_ole_santander"
        if not is_fatura_ole and profile == "auto":
            is_fatura_ole = (
                ("OLE" in probe_text or "OLÉ" in probe_text or "SANTANDER" in probe_text) and
                ("CARTAO" in probe_text or "CARTÃO" in probe_text) and
                ("VCTO" in probe_text or "VENCIMENTO" in probe_text) and
                ("DT_MOV" in probe_text or "DESCRICAO" in probe_text or "DESCRIÇÃO" in probe_text) and
                ("DEBITO" in probe_text or "DÉBITO" in probe_text) and
                ("CREDITO" in probe_text or "CRÉDITO" in probe_text)
            )
        
        if is_fatura_ole:
            report_progress(15, "Processando Fatura Olé-Santander...")
            data, linhas = _parse_fatura_ole_santander(file_bytes, progress_callback)
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data
        
        # ── Contracheque AmazonPrev ──────────────────────────────
        is_amazonprev = profile == "contracheque_amazonprev"
        if not is_amazonprev and profile == "auto":
            is_amazonprev = (
                "AMAZONPREV" in probe_text and
                ("CONTRACHEQUE" in probe_text or "PENSIONISTA" in probe_text) and
                ("GANHOS" in probe_text and "DESCONTOS" in probe_text)
            )
        
        if is_amazonprev:
            report_progress(15, "Processando Contracheque AmazonPrev...")
            data, linhas = _parse_contracheque_amazonprev(file_bytes, progress_callback)
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data
        
        # ── Histórico de Créditos INSS ───────────────────────────
        is_historico_inss = profile == "historico_creditos_inss"
        if not is_historico_inss and profile == "auto":
            is_historico_inss = (
                "INSS" in probe_text and
                ("HIST" in probe_text and "CR" in probe_text) and  # HISTÓRICO DE CRÉDITOS
                ("RUBRICA" in probe_text) and
                ("NIT" in probe_text or "FILIADO" in probe_text)
            )
        
        if is_historico_inss:
            report_progress(15, "Processando Histórico INSS...")
            data, linhas = _parse_historico_inss(file_bytes, progress_callback)
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data
        
        # ── Contracheque SEMAD/PMM (Prefeitura de Manaus) ────────
        is_semad = profile in ("contracheque_semad", "contracheque_pmm")
        if not is_semad and profile == "auto":
            # Detecção mais abrangente para SEMAD/PMM
            is_semad = (
                (
                    "SEMAD" in probe_text or 
                    "PREFEITURA MUNICIPAL DE MANAUS" in probe_text or
                    "PREFEITURA DE MANAUS" in probe_text or
                    "PMM" in probe_text or
                    "MANAUSPREV" in probe_text
                ) and
                (
                    "CONTRACHEQUE" in probe_text or
                    ("COD" in probe_text and "DESCRIÇÃO" in probe_text) or
                    ("CÓDIGO" in probe_text and "DESCRIÇÃO" in probe_text)
                ) and
                ("GANHOS" in probe_text or "DESCONTOS" in probe_text or "VENCIMENTOS" in probe_text)
            )
        
        if is_semad:
            report_progress(15, "Processando Contracheque SEMAD/PMM...")
            data, linhas = _parse_contracheque_semad(file_bytes, progress_callback)
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data
        
        # ── Contracheque SEAD / Ficha Financeira SEAD ─────────
        is_sead = profile in ("contracheque_sead", "ficha_financeira_sead")
        if not is_sead and profile == "auto":
            is_sead = (
                (
                    "SEAD" in probe_text or 
                    "GOVERNO DO ESTADO DO AMAZONAS" in probe_text or
                    "GOVERNO DO AMAZONAS" in probe_text or
                    "SECRETARIA DE ESTADO DE ADMINISTRA" in probe_text
                ) and
                (
                    "CONTRACHEQUE" in probe_text or
                    "FICHA FINANCEIRA" in probe_text or
                    ("COD" in probe_text and ("DESCRICAO" in probe_text or "DESCRIÇÃO" in probe_text))
                ) and
                ("GANHO" in probe_text or "DESCONTO" in probe_text or "GANHOS" in probe_text or "DESCONTOS" in probe_text or "VENCIMENTOS" in probe_text)
            )
        
        if is_sead:
            # Detectar se é Ficha Financeira (formato com meses por nome) ou contracheque normal
            is_ficha = "FICHA FINANCEIRA" in probe_text or any(
                m in probe_text for m in ["JANEIRO/", "FEVEREIRO/", "MARCO/", "MARÇO/", "ABRIL/", "MAIO/", "JUNHO/", "JULHO/", "AGOSTO/", "SETEMBRO/", "OUTUBRO/", "NOVEMBRO/", "DEZEMBRO/"]
            )
            
            if is_ficha:
                report_progress(15, "Processando Ficha Financeira SEAD...")
                data, linhas = _parse_ficha_financeira_sead(file_bytes, progress_callback)
            else:
                report_progress(15, "Processando Contracheque SEAD/Governo AM...")
                data, linhas = _parse_contracheque_semad(file_bytes, progress_callback)
                if not data.orgao or data.orgao == "SEMAD/Prefeitura de Manaus":
                    data.orgao = "SEAD/Governo do Amazonas"
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data
        
        # ── Ficha Financeira SEMAD ───────────────────────────────
        is_ficha_semad = profile == "ficha_financeira_semad"
        if not is_ficha_semad and profile == "auto":
            is_ficha_semad = (
                ("SEMAD" in probe_text or "PREFEITURA" in probe_text) and
                "FICHA FINANCEIRA" in probe_text and
                ("GANHOS" in probe_text or "DESCONTOS" in probe_text)
            )
        
        if is_ficha_semad:
            report_progress(15, "Processando Ficha Financeira SEMAD...")
            data, linhas = _parse_contracheque_semad(file_bytes, progress_callback)
            if not data.orgao:
                data.orgao = "SEMAD/Prefeitura de Manaus - Ficha Financeira"
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data
        
        # ── Contracheque Pres. Figueiredo ────────────────────────
        is_figueiredo = profile == "contracheque_figueiredo"
        if not is_figueiredo and profile == "auto":
            is_figueiredo = (
                ("FIGUEIREDO" in probe_text or "PRESIDENTE FIGUEIREDO" in probe_text) and
                ("CONTRACHEQUE" in probe_text or "GANHOS" in probe_text or "DESCONTOS" in probe_text)
            )
        
        if is_figueiredo:
            report_progress(15, "Processando Contracheque Pres. Figueiredo...")
            data, linhas = _parse_contracheque_semad(file_bytes, progress_callback)
            if not data.orgao:
                data.orgao = "Prefeitura Municipal de Presidente Figueiredo"
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data
        
        # ── Demonstrativo SIAPE/IFAM ─────────────────────────────
        is_siape = profile == "demonstrativo_siape"
        if not is_siape and profile == "auto":
            is_siape = (
                ("SIAPE" in probe_text or "IFAM" in probe_text or "INSTITUTO FEDERAL" in probe_text) and
                ("DEMONSTRATIVO" in probe_text or "RENDIMENTO" in probe_text) and
                ("GANHOS" in probe_text or "DESCONTOS" in probe_text or "VENCIMENTOS" in probe_text)
            )
        
        if is_siape:
            report_progress(15, "Processando Demonstrativo SIAPE/IFAM...")
            data, linhas = _parse_contracheque_semad(file_bytes, progress_callback)
            if not data.orgao:
                data.orgao = "SIAPE/IFAM"
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data
        
        # ── Extrato bancário ─────────────────────────────────────
        is_extrato = profile == "extrato_bancario"
        if not is_extrato and profile == "auto":
            is_extrato = (
                ("DÉBITO" in probe_text or "DEBITO" in probe_text) and
                ("CRÉDITO" in probe_text or "CREDITO" in probe_text) and
                ("SALDO" in probe_text) and
                ("HISTÓRICO" in probe_text or "HISTORICO" in probe_text)
            )

        if is_extrato:
            report_progress(15, "Processando Extrato Bancário...")
            data, linhas = _parse_extrato_bancario(file_bytes, progress_callback)
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data

        # ── Contracheque Genérico (qualquer documento com tabela de rubricas) ──
        # Detecta documentos com estrutura de contracheque: COD + DESCRIÇÃO + GANHOS/DESCONTOS
        is_contracheque_generico = profile == "contracheque"
        if not is_contracheque_generico and profile == "auto":
            is_contracheque_generico = (
                (
                    ("COD" in probe_text or "CÓDIGO" in probe_text or "CODIGO" in probe_text) and
                    ("DESCRIÇÃO" in probe_text or "DESCRICAO" in probe_text)
                ) and
                (
                    "GANHOS" in probe_text or 
                    "DESCONTOS" in probe_text or 
                    "VENCIMENTOS" in probe_text or
                    "PROVENTOS" in probe_text
                )
            )
        
        if is_contracheque_generico:
            report_progress(15, "Processando Contracheque...")
            # Usar o parser SEMAD que é mais robusto e retorna datas no formato correto
            data, linhas = _parse_contracheque_semad(file_bytes, progress_callback)
            if not data.orgao:
                data.orgao = "Contracheque"
            import json
            data.raw_text = json.dumps(linhas, ensure_ascii=False)
            if keywords:
                data.transacoes = [
                    t for t in data.transacoes
                    if any(kw.lower() in t.descricao.lower() for kw in keywords)
                ]
            return data

        # ── Fallback: Extração de texto puro ─────────────────────
        # Para documentos que não se encaixam em nenhum perfil específico
        report_progress(15, "Extraindo texto do documento...")
        text = extract_text(file_bytes)
        data.raw_text = text
        upper = text.upper()

        report_progress(40, "Extraindo informações pessoais...")
        _parse_personal_info(text, data)

        report_progress(60, "Processando transações...")
        # Tentar extrair transações do texto
        data.transacoes = _parse_contracheque(text, data.competencia)

        if not data.transacoes:
            report_progress(70, "Processando contratos...")
            data.contratos = _parse_contratos(text)

        report_progress(80, "Detectando descontos indevidos...")
        data.descontos_indevidos = _detect_descontos_indevidos(text)

        if keywords:
            data.transacoes = [
                t for t in data.transacoes
                if any(kw.lower() in t.descricao.lower() for kw in keywords)
            ]

        report_progress(90, "Finalizando processamento...")
        logger.info("PDF processado: %d transações, %d contratos",
                    len(data.transacoes), len(data.contratos))
    except Exception as exc:
        logger.exception("Erro ao processar PDF: %s", exc)
        raise

    return data
