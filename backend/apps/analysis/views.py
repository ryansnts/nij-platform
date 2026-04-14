from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from apps.documents.models import Document
from .models import AnalysisResult
from .serializers import AnalysisResultSerializer
from . import bcb_service
import logging

logger = logging.getLogger(__name__)


class AnalysisResultDetailView(generics.RetrieveAPIView):
    serializer_class = AnalysisResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        doc_qs = Document.objects.all() if user.role == "admin" else Document.objects.filter(uploaded_by=user)
        try:
            doc = doc_qs.get(pk=self.kwargs["document_id"])
        except Document.DoesNotExist:
            raise NotFound("Documento não encontrado.")
        try:
            return doc.analysis_result
        except AnalysisResult.DoesNotExist:
            raise NotFound("Análise ainda não disponível.")


class BCBSeriesListView(APIView):
    """
    Lista as séries disponíveis do Banco Central.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        series = bcb_service.get_available_series()
        return Response({
            "series": [
                {"codigo": codigo, "nome": nome}
                for nome, codigo in series.items()
            ]
        })


class BCBSeriesDataView(APIView):
    """
    Busca dados de uma série temporal do Banco Central.
    
    Query params:
        - codigo: Código da série (ex: 188 para INPC)
        - data_inicio: Data inicial (DD/MM/AAAA)
        - data_fim: Data final (DD/MM/AAAA)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        codigo = request.query_params.get('codigo')
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        
        if not all([codigo, data_inicio, data_fim]):
            return Response(
                {"error": "Parâmetros obrigatórios: codigo, data_inicio, data_fim"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            codigo = int(codigo)
            data = bcb_service.fetch_bcb_series(codigo, data_inicio, data_fim)
            return Response({
                "codigo": codigo,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "registros": len(data),
                "dados": data
            })
        except ValueError:
            return Response(
                {"error": "Código da série deve ser um número inteiro"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao buscar série BCB: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class INPCFactorsView(APIView):
    """
    Calcula os fatores de correção INPC para múltiplas datas.
    
    POST body:
        {
            "datas_pagamento": ["01/01/2020", "01/02/2020", ...],
            "data_atualizacao": "01/01/2025"
        }
    
    Returns:
        {
            "fatores": {
                "01/01/2020": 1.234567,
                "01/02/2020": 1.223456,
                ...
            },
            "data_atualizacao": "01/01/2025"
        }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        datas_pagamento = request.data.get('datas_pagamento', [])
        data_atualizacao = request.data.get('data_atualizacao')
        
        if not datas_pagamento or not data_atualizacao:
            return Response(
                {"error": "Parâmetros obrigatórios: datas_pagamento (lista), data_atualizacao"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            fatores = bcb_service.get_inpc_factors_for_dates(datas_pagamento, data_atualizacao)
            return Response({
                "fatores": fatores,
                "data_atualizacao": data_atualizacao,
                "total_datas": len(fatores)
            })
        except Exception as e:
            logger.error(f"Erro ao calcular fatores INPC: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class INPCSeriesView(APIView):
    """
    Busca a série completa do INPC entre duas datas.
    
    Query params:
        - data_inicio: Data inicial (DD/MM/AAAA)
        - data_fim: Data final (DD/MM/AAAA)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        
        if not all([data_inicio, data_fim]):
            return Response(
                {"error": "Parâmetros obrigatórios: data_inicio, data_fim"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = bcb_service.get_inpc_series(data_inicio, data_fim)
            
            # Converter para formato mais amigável
            formatted_data = []
            for item in data:
                try:
                    valor = float(item['valor'].replace(',', '.')) if isinstance(item['valor'], str) else float(item['valor'])
                    formatted_data.append({
                        "data": item['data'],
                        "valor": valor,
                        "fator": round(1 + valor / 100, 6)
                    })
                except (ValueError, KeyError):
                    continue
            
            return Response({
                "indice": "INPC",
                "codigo_bcb": 188,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "registros": len(formatted_data),
                "dados": formatted_data
            })
        except Exception as e:
            logger.error(f"Erro ao buscar série INPC: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
