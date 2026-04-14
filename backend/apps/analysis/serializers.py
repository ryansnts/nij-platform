from rest_framework import serializers
from .models import AnalysisResult


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = [
            "id", "nome", "cpf", "matricula", "orgao", "competencia",
            "valor_bruto", "valor_liquido",
            "margem_consignavel", "margem_utilizada", "margem_disponivel",
            "transacoes", "contratos", "descontos_indevidos", "codigos_rmc",
            "raw_text", "created_at",
        ]
