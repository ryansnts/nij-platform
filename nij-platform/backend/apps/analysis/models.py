from django.db import models
from apps.documents.models import Document


class AnalysisResult(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name="analysis_result"
    )
    # Personal info
    nome = models.CharField(max_length=255, blank=True)
    cpf = models.CharField(max_length=20, blank=True)
    matricula = models.CharField(max_length=50, blank=True)
    orgao = models.CharField(max_length=255, blank=True)
    competencia = models.CharField(max_length=50, blank=True)
    # Financial summary
    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_liquido = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    margem_consignavel = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    margem_utilizada = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    margem_disponivel = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # Raw extracted data (JSON)
    transacoes = models.JSONField(default=list)
    contratos = models.JSONField(default=list)
    descontos_indevidos = models.JSONField(default=list)
    codigos_rmc = models.JSONField(default=list)
    # Raw text (for debugging)
    raw_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analysis_results"

    def __str__(self):
        return f"Análise: {self.document.original_filename}"
