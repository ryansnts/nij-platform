import uuid
from django.db import models
from django.conf import settings


def upload_path(instance, filename):
    return f"documents/{instance.uploaded_by.id}/{uuid.uuid4()}/{filename}"


class Document(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PROCESSING = "processing", "Processando"
        COMPLETED = "completed", "Concluído"
        ERROR = "error", "Erro"
        CANCELLED = "cancelled", "Cancelado"

    class ExtractionProfile(models.TextChoices):
        # 1 - Detecção Automática
        AUTO = "auto", "1 - Detecção Automática"
        # 2 - Histórico de Crédito INSS
        HISTORICO_INSS = "historico_creditos_inss", "2 - Histórico de Crédito INSS"
        # 3 - Demonstrativo de Rendimento Anual (SIAPE/IFAM)
        DEMONSTRATIVO_SIAPE = "demonstrativo_siape", "3 - Demonstrativo Rendimento Anual (SIAPE/IFAM)"
        # 4 - Fundação AmazonPrev
        CONTRACHEQUE_AMAZONPREV = "contracheque_amazonprev", "4 - Fundação AmazonPrev"
        # 5 - Contracheque PMM AM
        CONTRACHEQUE_PMM = "contracheque_pmm", "5 - Contracheque PMM AM"
        # 6 - Contracheque SEMAD/Prefeitura Manaus
        CONTRACHEQUE_SEMAD = "contracheque_semad", "6 - Contracheque SEMAD/Pref. Manaus"
        # 7 - Ficha Financeira SEMAD
        FICHA_SEMAD = "ficha_financeira_semad", "7 - Ficha Financeira SEMAD"
        # 8 - Contracheque SEAD/Governo AM
        CONTRACHEQUE_SEAD = "contracheque_sead", "8 - Contracheque SEAD/Governo AM"
        # 9 - Ficha Financeira SEAD/Governo AM
        FICHA_SEAD = "ficha_financeira_sead", "9 - Ficha Financeira SEAD/Governo AM"
        # 10 - Pref. Munic. de Pres. Figueiredo
        CONTRACHEQUE_FIGUEIREDO = "contracheque_figueiredo", "10 - Pref. Munic. Pres. Figueiredo"
        # 11 - Extratos Bancários
        EXTRATO_BANCARIO = "extrato_bancario", "11 - Extratos Bancários"
        # 12 - Fatura Cartão Olé-Santander
        FATURA_OLE_SANTANDER = "fatura_ole_santander", "12 - Fatura Cartão Olé-Santander"
        # Outros (legado)
        CONTRACHEQUE = "contracheque", "Contracheque Genérico"
        INSS_CARTAO = "inss_cartao", "Extrato INSS Cartão"
        FATURA = "fatura", "Fatura Cartão RMC"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=upload_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    extraction_profile = models.CharField(
        max_length=50, choices=ExtractionProfile.choices, default=ExtractionProfile.AUTO
    )
    search_keywords = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    
    # Campos de progresso
    progress = models.PositiveIntegerField(default=0)  # 0-100
    progress_message = models.CharField(max_length=255, blank=True)
    total_pages = models.PositiveIntegerField(default=0)
    current_page = models.PositiveIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True)
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.status})"
