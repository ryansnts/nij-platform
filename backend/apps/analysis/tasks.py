import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def update_progress(doc, progress: int, message: str, current_page: int = 0, total_pages: int = 0):
    """Atualiza o progresso do documento no banco."""
    from apps.documents.models import Document
    
    # Recarregar para verificar se foi cancelado
    doc.refresh_from_db()
    if doc.status == Document.Status.CANCELLED:
        raise Exception("Processamento cancelado pelo usuário")
    
    doc.progress = progress
    doc.progress_message = message
    doc.current_page = current_page
    doc.total_pages = total_pages
    doc.save(update_fields=["progress", "progress_message", "current_page", "total_pages", "updated_at"])


@shared_task(bind=True, max_retries=3, queue="pdf_processing")
def process_document_task(self, document_id: str):
    """Async Celery task: process a PDF document and save analysis result."""
    from apps.documents.models import Document
    from .models import AnalysisResult
    from .pdf_processor import process_pdf

    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.error("Document %s not found", document_id)
        return

    # Verificar se já foi cancelado
    if doc.status == Document.Status.CANCELLED:
        logger.info("Document %s was cancelled before processing started", document_id)
        return

    doc.status = Document.Status.PROCESSING
    doc.progress = 0
    doc.progress_message = "Iniciando processamento..."
    doc.save(update_fields=["status", "progress", "progress_message", "updated_at"])

    try:
        file_bytes = doc.file.read()
        
        # Callback de progresso
        def progress_callback(progress: int, message: str, current_page: int = 0, total_pages: int = 0):
            update_progress(doc, progress, message, current_page, total_pages)
        
        result = process_pdf(
            file_bytes,
            profile=doc.extraction_profile,
            keywords=doc.search_keywords or None,
            progress_callback=progress_callback,
        )

        # Verificar cancelamento antes de salvar
        doc.refresh_from_db()
        if doc.status == Document.Status.CANCELLED:
            logger.info("Document %s was cancelled during processing", document_id)
            return

        update_progress(doc, 95, "Salvando resultados...")

        AnalysisResult.objects.update_or_create(
            document=doc,
            defaults={
                "nome": result.nome,
                "cpf": result.cpf,
                "matricula": result.matricula,
                "orgao": result.orgao,
                "competencia": result.competencia,
                "valor_bruto": result.valor_bruto,
                "valor_liquido": result.valor_liquido,
                "margem_consignavel": result.margem_consignavel,
                "margem_utilizada": result.margem_utilizada,
                "margem_disponivel": result.margem_disponivel,
                "transacoes": [
                    {"data": t.data, "descricao": t.descricao,
                     "valor": t.valor, "tipo": t.tipo, "codigoRMC": t.codigo_rmc}
                    for t in result.transacoes
                ],
                "contratos": [
                    {"numero": c.numero, "banco": c.banco, "tipo": c.tipo,
                     "parcela": c.parcela, "totalParcelas": c.total_parcelas,
                     "valorParcela": c.valor_parcela, "saldoDevedor": c.saldo_devedor,
                     "taxaJuros": c.taxa_juros}
                    for c in result.contratos
                ],
                "descontos_indevidos": [
                    {"descricao": d.descricao, "valor": d.valor,
                     "tipo": d.tipo, "status": d.status}
                    for d in result.descontos_indevidos
                ],
                "raw_text": result.raw_text,  # JSON array completo
            },
        )

        doc.status = Document.Status.COMPLETED
        doc.progress = 100
        doc.progress_message = "Concluído!"
        doc.save(update_fields=["status", "progress", "progress_message", "updated_at"])
        logger.info("Document %s processed successfully", document_id)

    except Exception as exc:
        # Verificar se foi cancelamento
        doc.refresh_from_db()
        if doc.status == Document.Status.CANCELLED:
            logger.info("Document %s processing was cancelled", document_id)
            return
            
        logger.exception("Error processing document %s: %s", document_id, exc)
        doc.status = Document.Status.ERROR
        doc.error_message = str(exc)
        doc.progress_message = "Erro no processamento"
        doc.save(update_fields=["status", "error_message", "progress_message", "updated_at"])
        raise self.retry(exc=exc, countdown=60)
