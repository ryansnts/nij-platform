"""
Serviço para consulta de índices econômicos do Banco Central do Brasil.
Utiliza a API pública do SGS (Sistema Gerenciador de Séries Temporais).

Documentação: https://www3.bcb.gov.br/sgspub/
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Códigos das séries no SGS do Banco Central
SERIES_CODES = {
    'INPC': 188,           # INPC - Índice Nacional de Preços ao Consumidor
    'IPCA': 433,           # IPCA - Índice Nacional de Preços ao Consumidor Amplo
    'IGP-M': 189,          # IGP-M - Índice Geral de Preços do Mercado
    'IGP-DI': 190,         # IGP-DI - Índice Geral de Preços - Disponibilidade Interna
    'SELIC': 432,          # Taxa SELIC
    'CDI': 12,             # Taxa CDI
    'TR': 226,             # Taxa Referencial
    'POUPANCA': 25,        # Rendimento da Poupança
    # Taxas de juros de crédito consignado
    'JUROS_CONSIGNADO_PUBLICO': 25467,  # Taxa média mensal - Crédito consignado setor público
    'JUROS_CONSIGNADO_INSS': 25468,     # Taxa média mensal - Crédito consignado aposentados INSS
}

BCB_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"


def fetch_bcb_series(
    codigo: int,
    data_inicio: str,
    data_fim: str,
    formato: str = "json"
) -> List[Dict]:
    """
    Busca dados de uma série temporal do BCB.
    
    Args:
        codigo: Código da série no SGS
        data_inicio: Data inicial no formato DD/MM/AAAA
        data_fim: Data final no formato DD/MM/AAAA
        formato: Formato de retorno (json ou xml)
    
    Returns:
        Lista de dicionários com 'data' e 'valor'
    """
    url = BCB_API_URL.format(codigo=codigo)
    params = {
        "formato": formato,
        "dataInicial": data_inicio,
        "dataFinal": data_fim
    }
    
    try:
        logger.info(f"Buscando série {codigo} do BCB: {data_inicio} a {data_fim}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Recebidos {len(data)} registros da série {codigo}")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar série {codigo} do BCB: {e}")
        raise Exception(f"Erro ao consultar API do Banco Central: {str(e)}")


def get_inpc_series(data_inicio: str, data_fim: str) -> List[Dict]:
    """
    Busca a série do INPC (código 188) do BCB.
    
    Args:
        data_inicio: Data inicial no formato DD/MM/AAAA
        data_fim: Data final no formato DD/MM/AAAA
    
    Returns:
        Lista de dicionários com 'data' (MM/AAAA) e 'valor' (variação mensal %)
    """
    return fetch_bcb_series(SERIES_CODES['INPC'], data_inicio, data_fim)


def calculate_inpc_factor(
    data_base: str,
    data_atualizacao: str,
    inpc_data: Optional[List[Dict]] = None
) -> Tuple[float, List[Dict]]:
    """
    Calcula o fator de correção INPC acumulado entre duas datas.
    
    O fator é calculado como o produto de (1 + taxa/100) para cada mês.
    
    Args:
        data_base: Data base no formato DD/MM/AAAA (data do pagamento original)
        data_atualizacao: Data de atualização no formato DD/MM/AAAA
        inpc_data: Dados do INPC já carregados (opcional, para evitar múltiplas requisições)
    
    Returns:
        Tupla com (fator_acumulado, lista_de_indices_utilizados)
    """
    # Parse das datas
    try:
        d_base = datetime.strptime(data_base, "%d/%m/%Y")
        d_atual = datetime.strptime(data_atualizacao, "%d/%m/%Y")
    except ValueError:
        raise ValueError("Formato de data inválido. Use DD/MM/AAAA")
    
    if d_base >= d_atual:
        return 1.0, []
    
    # Buscar dados do INPC se não fornecidos
    if inpc_data is None:
        # Buscar do mês seguinte à data base até o mês anterior à data de atualização
        inicio = (d_base.replace(day=1) + timedelta(days=32)).replace(day=1)
        fim = d_atual.replace(day=1) - timedelta(days=1)
        
        inpc_data = get_inpc_series(
            inicio.strftime("%d/%m/%Y"),
            fim.strftime("%d/%m/%Y")
        )
    
    # Calcular fator acumulado
    fator = 1.0
    indices_utilizados = []
    
    for item in inpc_data:
        try:
            valor = float(item['valor'].replace(',', '.')) if isinstance(item['valor'], str) else float(item['valor'])
            fator *= (1 + valor / 100)
            indices_utilizados.append({
                'data': item['data'],
                'valor': valor,
                'fator_parcial': 1 + valor / 100
            })
        except (ValueError, KeyError) as e:
            logger.warning(f"Erro ao processar índice INPC: {item}, erro: {e}")
            continue
    
    return round(fator, 6), indices_utilizados


def get_inpc_factors_for_dates(
    datas_pagamento: List[str],
    data_atualizacao: str
) -> Dict[str, float]:
    """
    Calcula os fatores de correção INPC para múltiplas datas de pagamento.
    
    Args:
        datas_pagamento: Lista de datas de pagamento no formato DD/MM/AAAA
        data_atualizacao: Data de atualização no formato DD/MM/AAAA
    
    Returns:
        Dicionário com data_pagamento -> fator_correcao
    """
    if not datas_pagamento:
        return {}
    
    # Encontrar a data mais antiga
    datas_parsed = []
    for d in datas_pagamento:
        try:
            datas_parsed.append(datetime.strptime(d, "%d/%m/%Y"))
        except ValueError:
            continue
    
    if not datas_parsed:
        return {}
    
    data_mais_antiga = min(datas_parsed)
    data_atual = datetime.strptime(data_atualizacao, "%d/%m/%Y")
    
    # Buscar todos os dados do INPC de uma vez
    inicio = data_mais_antiga.replace(day=1)
    fim = data_atual.replace(day=1)
    
    try:
        inpc_data = get_inpc_series(
            inicio.strftime("%d/%m/%Y"),
            fim.strftime("%d/%m/%Y")
        )
    except Exception as e:
        logger.error(f"Erro ao buscar INPC: {e}")
        return {d: 1.0 for d in datas_pagamento}
    
    # Converter para dicionário por mês/ano
    inpc_por_mes = {}
    for item in inpc_data:
        try:
            # Data vem no formato DD/MM/AAAA
            data_item = datetime.strptime(item['data'], "%d/%m/%Y")
            mes_ano = data_item.strftime("%m/%Y")
            valor = float(item['valor'].replace(',', '.')) if isinstance(item['valor'], str) else float(item['valor'])
            inpc_por_mes[mes_ano] = valor
        except (ValueError, KeyError):
            continue
    
    # Calcular fator para cada data de pagamento
    fatores = {}
    for data_pagto in datas_pagamento:
        try:
            d_pagto = datetime.strptime(data_pagto, "%d/%m/%Y")
            
            # Calcular fator acumulado do mês seguinte ao pagamento até o mês anterior à atualização
            fator = 1.0
            mes_atual = (d_pagto.replace(day=1) + timedelta(days=32)).replace(day=1)
            
            while mes_atual < data_atual:
                mes_ano = mes_atual.strftime("%m/%Y")
                if mes_ano in inpc_por_mes:
                    fator *= (1 + inpc_por_mes[mes_ano] / 100)
                mes_atual = (mes_atual + timedelta(days=32)).replace(day=1)
            
            fatores[data_pagto] = round(fator, 6)
            
        except ValueError:
            fatores[data_pagto] = 1.0
    
    return fatores


def get_available_series() -> Dict[str, int]:
    """
    Retorna as séries disponíveis para consulta.
    """
    return SERIES_CODES.copy()
