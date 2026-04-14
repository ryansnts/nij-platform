#!/usr/bin/env python
"""
Script de debug para contracheques AmazonPrev.
Execute dentro do container: docker-compose exec worker python debug_contracheque.py
"""
import sys
import os
import re
import pdfplumber

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from apps.documents.models import Document

# Pegar o documento mais recente
doc = Document.objects.order_by('-created_at').first()
if not doc:
    print("Nenhum documento encontrado!")
    sys.exit(1)

print(f"=" * 80)
print(f"Documento: {doc.original_filename}")
print(f"ID: {doc.id}")
print(f"Tamanho: {doc.file_size} bytes")
print(f"Perfil: {doc.extraction_profile}")
print(f"=" * 80)

# Regex para competência
COMP_PATTERNS = [
    re.compile(r"COMPET[ÊE]NCIA\s*\n?\s*(\d{1,2}/\d{4})", re.IGNORECASE),
    re.compile(r"COMPET[ÊE]NCIA[:\s]*(\d{1,2}/\d{4})", re.IGNORECASE),
    re.compile(r"(\d{1,2}/\d{4})\s*COMPET", re.IGNORECASE),
    re.compile(r"MES/ANO[:\s]*(\d{1,2}/\d{4})", re.IGNORECASE),
]

doc.file.seek(0)
with pdfplumber.open(doc.file) as pdf:
    print(f"\nTotal de páginas: {len(pdf.pages)}")
    print(f"=" * 80)
    
    competencias_encontradas = []
    
    for i, page in enumerate(pdf.pages):
        print(f"\n{'='*40} PÁGINA {i+1} {'='*40}")
        
        # Extrair texto
        text = page.extract_text() or ""
        
        # Mostrar primeiras 50 linhas do texto
        lines = text.split("\n")
        print(f"\n--- Texto extraído ({len(text)} chars, {len(lines)} linhas) ---")
        for j, line in enumerate(lines[:50]):
            print(f"  {j:3d}: {line}")
        
        # Buscar competência com diferentes padrões
        print(f"\n--- Busca de COMPETÊNCIA ---")
        comp_found = False
        for pattern in COMP_PATTERNS:
            match = pattern.search(text)
            if match:
                comp = match.group(1)
                print(f"  ENCONTRADO: '{comp}' (padrão: {pattern.pattern})")
                competencias_encontradas.append((i+1, comp))
                comp_found = True
                break
        
        if not comp_found:
            # Buscar qualquer menção de competência
            comp_mentions = re.findall(r".{0,30}COMPET.{0,30}", text, re.IGNORECASE)
            if comp_mentions:
                print(f"  Menções de 'COMPET' encontradas:")
                for m in comp_mentions[:5]:
                    print(f"    -> '{m.strip()}'")
            else:
                print(f"  NENHUMA menção de 'COMPET' encontrada!")
            
            # Buscar datas no formato MM/AAAA
            datas = re.findall(r"\b(\d{1,2}/\d{4})\b", text)
            if datas:
                print(f"  Datas MM/AAAA encontradas: {datas[:10]}")
        
        # Extrair tabelas
        tables = page.extract_tables()
        print(f"\n--- Tabelas encontradas: {len(tables) if tables else 0} ---")
        
        if tables:
            for j, table in enumerate(tables):
                if not table:
                    continue
                print(f"\n  Tabela {j+1} ({len(table)} linhas):")
                for row_idx, row in enumerate(table[:8]):
                    print(f"    {row_idx}: {row}")
        
        # Limitar a 5 páginas para não poluir muito
        if i >= 4:
            print(f"\n... (mostrando apenas primeiras 5 páginas de {len(pdf.pages)})")
            break
    
    print(f"\n{'='*80}")
    print(f"RESUMO: Competências encontradas em {len(competencias_encontradas)} páginas:")
    for pg, comp in competencias_encontradas:
        print(f"  Página {pg}: {comp}")
    
    # Verificar se há páginas sem competência
    paginas_com_comp = {pg for pg, _ in competencias_encontradas}
    paginas_sem_comp = [i+1 for i in range(min(5, len(pdf.pages))) if (i+1) not in paginas_com_comp]
    if paginas_sem_comp:
        print(f"\nPáginas SEM competência detectada: {paginas_sem_comp}")
