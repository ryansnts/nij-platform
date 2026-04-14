#!/usr/bin/env python
"""
Script de teste para verificar o processador de PDF SEMAD/PMM.
Execute: python test_semad_processor.py <caminho_do_pdf>
"""
import sys
import json
from pathlib import Path

# Adicionar o diretório do projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

from apps.analysis.pdf_processor import process_pdf


def test_processor(pdf_path: str, profile: str = "auto"):
    """Testa o processador de PDF com um arquivo específico."""
    print(f"\n{'='*60}")
    print(f"Testando: {pdf_path}")
    print(f"Perfil: {profile}")
    print(f"{'='*60}\n")
    
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    
    def progress_callback(progress, message, current_page=0, total_pages=0):
        if total_pages > 0:
            print(f"  [{progress:3d}%] {message} (página {current_page}/{total_pages})")
        else:
            print(f"  [{progress:3d}%] {message}")
    
    result = process_pdf(file_bytes, profile=profile, progress_callback=progress_callback)
    
    print(f"\n{'─'*60}")
    print("RESULTADO:")
    print(f"{'─'*60}")
    print(f"  Nome: {result.nome}")
    print(f"  CPF: {result.cpf}")
    print(f"  Matrícula: {result.matricula}")
    print(f"  Órgão: {result.orgao}")
    print(f"  Competência: {result.competencia}")
    print(f"  Valor Bruto: R$ {result.valor_bruto:,.2f}" if result.valor_bruto else "  Valor Bruto: —")
    print(f"  Valor Líquido: R$ {result.valor_liquido:,.2f}" if result.valor_liquido else "  Valor Líquido: —")
    print(f"  Total Transações: {len(result.transacoes)}")
    
    # Contar débitos e créditos
    debitos = [t for t in result.transacoes if t.tipo == "debito"]
    creditos = [t for t in result.transacoes if t.tipo == "credito"]
    total_debitos = sum(t.valor for t in debitos)
    total_creditos = sum(t.valor for t in creditos)
    
    print(f"    - Débitos: {len(debitos)} (R$ {total_debitos:,.2f})")
    print(f"    - Créditos: {len(creditos)} (R$ {total_creditos:,.2f})")
    
    # Mostrar primeiras 10 transações
    if result.transacoes:
        print(f"\n{'─'*60}")
        print("PRIMEIRAS 10 TRANSAÇÕES:")
        print(f"{'─'*60}")
        for i, t in enumerate(result.transacoes[:10]):
            tipo_str = "DÉB" if t.tipo == "debito" else "CRÉ"
            print(f"  {i+1:3d}. [{tipo_str}] {t.data} | R$ {t.valor:>10,.2f} | {t.descricao[:50]}")
    
    # Verificar formato das datas
    print(f"\n{'─'*60}")
    print("VERIFICAÇÃO DE FORMATO DE DATAS:")
    print(f"{'─'*60}")
    if result.transacoes:
        sample_dates = [t.data for t in result.transacoes[:5]]
        for d in sample_dates:
            is_valid = len(d.split("/")) == 3 and len(d) >= 8
            status = "✓ OK (DD/MM/AAAA)" if is_valid else "✗ ERRO (esperado DD/MM/AAAA)"
            print(f"  {d} → {status}")
    
    # Verificar raw_text (JSON de linhas)
    print(f"\n{'─'*60}")
    print("VERIFICAÇÃO DE RAW_TEXT (JSON):")
    print(f"{'─'*60}")
    try:
        linhas = json.loads(result.raw_text)
        if isinstance(linhas, list):
            print(f"  ✓ raw_text é um array JSON com {len(linhas)} linhas")
            if linhas:
                print(f"  Exemplo de linha: {json.dumps(linhas[0], ensure_ascii=False)[:100]}...")
        else:
            print(f"  ✗ raw_text não é um array (tipo: {type(linhas).__name__})")
    except json.JSONDecodeError:
        print(f"  ✗ raw_text não é JSON válido (texto puro)")
    
    print(f"\n{'='*60}")
    print("TESTE CONCLUÍDO")
    print(f"{'='*60}\n")
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_semad_processor.py <caminho_do_pdf> [perfil]")
        print("\nPerfis disponíveis:")
        print("  - auto (detecção automática)")
        print("  - contracheque_semad")
        print("  - contracheque_pmm")
        print("  - contracheque_amazonprev")
        print("  - historico_creditos_inss")
        print("  - fatura_ole_santander")
        print("  - extrato_bancario")
        print("  - contracheque_sead")
        print("  - demonstrativo_siape")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    profile = sys.argv[2] if len(sys.argv) > 2 else "auto"
    
    if not Path(pdf_path).exists():
        print(f"Erro: Arquivo não encontrado: {pdf_path}")
        sys.exit(1)
    
    test_processor(pdf_path, profile)
