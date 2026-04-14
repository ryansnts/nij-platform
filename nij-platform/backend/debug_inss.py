#!/usr/bin/env python
"""
Script de debug para Histórico de Créditos INSS.
Execute dentro do container: docker-compose exec worker python /app/debug_inss.py
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
print(f"=" * 80)

doc.file.seek(0)
with pdfplumber.open(doc.file) as pdf:
    print(f"\nTotal de páginas: {len(pdf.pages)}")
    
    for i, page in enumerate(pdf.pages[:3]):  # Primeiras 3 páginas
        print(f"\n{'='*40} PÁGINA {i+1} {'='*40}")
        
        # Extrair texto
        text = page.extract_text() or ""
        lines = text.split("\n")
        
        print(f"\n--- Texto ({len(lines)} linhas) ---")
        for j, line in enumerate(lines):
            print(f"  {j:3d}: {line}")
        
        # Extrair tabelas
        tables = page.extract_tables()
        print(f"\n--- Tabelas: {len(tables) if tables else 0} ---")
        
        if tables:
            for t_idx, table in enumerate(tables):
                if not table:
                    continue
                print(f"\n  Tabela {t_idx+1} ({len(table)} linhas):")
                for row_idx, row in enumerate(table):
                    print(f"    {row_idx}: {row}")
        
        print("\n" + "=" * 80)
