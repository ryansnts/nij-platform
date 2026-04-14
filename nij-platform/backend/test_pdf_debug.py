#!/usr/bin/env python
"""
Script de debug para testar extração de PDF diretamente.
Execute dentro do container: docker-compose exec worker python test_pdf_debug.py
"""
import sys
import os
import re
import pdfplumber

# Adicionar o diretório ao path
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

print(f"Documento: {doc.original_filename}")
print(f"ID: {doc.id}")
print(f"Status: {doc.status}")
print("-" * 80)

# Ler o arquivo
file_bytes = doc.file.read()
print(f"Tamanho do arquivo: {len(file_bytes)} bytes")
print("-" * 80)

# Extrair texto com pdfplumber
with pdfplumber.open(doc.file) as pdf:
    print(f"Número de páginas: {len(pdf.pages)}")
    print("-" * 80)
    
    for i, page in enumerate(pdf.pages):
        print(f"\n=== PÁGINA {i+1} ===")
        
        # Extrair texto
        text = page.extract_text() or ""
        print(f"Texto extraído ({len(text)} chars):")
        print(text[:2000])
        print("-" * 40)
        
        # Extrair tabelas
        tables = page.extract_tables()
        print(f"\nTabelas encontradas: {len(tables) if tables else 0}")
        
        if tables:
            for j, table in enumerate(tables):
                print(f"\n--- Tabela {j+1} ({len(table)} linhas) ---")
                for row_idx, row in enumerate(table[:10]):  # Primeiras 10 linhas
                    print(f"  Linha {row_idx}: {row}")
        
        print("\n" + "=" * 80)
        
        # Só mostrar primeira página para não poluir
        if i >= 0:
            break

# Testar regex de data
print("\n=== TESTE DE REGEX ===")
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")
VALUE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")

doc.file.seek(0)
with pdfplumber.open(doc.file) as pdf:
    for page in pdf.pages[:1]:
        text = page.extract_text() or ""
        lines = text.split("\n")
        
        print(f"\nAnalisando {len(lines)} linhas...")
        for line_idx, line in enumerate(lines[:30]):
            line = line.strip()
            if not line:
                continue
            
            dates = DATE_RE.findall(line)
            values = VALUE_RE.findall(line)
            
            if dates or values:
                print(f"Linha {line_idx}: {line[:80]}")
                if dates:
                    print(f"  -> Datas: {dates}")
                if values:
                    print(f"  -> Valores: {values}")
