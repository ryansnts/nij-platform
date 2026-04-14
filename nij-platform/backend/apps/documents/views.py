from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.audit.services import log_action
from apps.analysis.tasks import process_document_task
from core.celery import app as celery_app
from .models import Document
from .serializers import DocumentUploadSerializer, DocumentSerializer


class DocumentUploadView(generics.CreateAPIView):
    serializer_class = DocumentUploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        doc = serializer.save()
        log_action(
            self.request.user,
            "DOCUMENT_UPLOAD",
            f'Arquivo "{doc.original_filename}" enviado para processamento',
            self.request,
        )
        # Dispatch async task
        task = process_document_task.apply_async(args=[str(doc.id)], queue="pdf_processing")
        # Salvar task_id para poder cancelar depois
        doc.celery_task_id = task.id
        doc.save(update_fields=["celery_task_id"])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        doc = serializer.instance
        return Response(
            DocumentSerializer(doc).data,
            status=status.HTTP_202_ACCEPTED,
        )


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Document.objects.select_related("uploaded_by", "analysis_result").all()
        return Document.objects.select_related("uploaded_by", "analysis_result").filter(
            uploaded_by=user
        )


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Document.objects.select_related("uploaded_by", "analysis_result").all()
        return Document.objects.select_related("uploaded_by", "analysis_result").filter(
            uploaded_by=user
        )

    def perform_destroy(self, instance):
        log_action(
            self.request.user,
            "DOCUMENT_DELETE",
            f'Documento "{instance.original_filename}" removido',
            self.request,
        )
        instance.file.delete(save=False)
        instance.delete()


class DocumentReprocessView(APIView):
    """Reprocessa um documento existente."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        qs = Document.objects.all() if user.role == "admin" else Document.objects.filter(uploaded_by=user)
        
        try:
            doc = qs.get(pk=pk)
        except Document.DoesNotExist:
            return Response({"detail": "Documento não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
        # Resetar status e limpar análise anterior
        doc.status = Document.Status.PENDING
        doc.error_message = ""
        doc.progress = 0
        doc.progress_message = ""
        doc.total_pages = 0
        doc.current_page = 0
        doc.save(update_fields=["status", "error_message", "progress", "progress_message", "total_pages", "current_page", "updated_at"])
        
        # Deletar análise anterior se existir
        if hasattr(doc, "analysis_result"):
            doc.analysis_result.delete()
        
        log_action(
            request.user,
            "DOCUMENT_REPROCESS",
            f'Documento "{doc.original_filename}" enviado para reprocessamento',
            request,
        )
        
        # Dispatch async task
        task = process_document_task.apply_async(args=[str(doc.id)], queue="pdf_processing")
        doc.celery_task_id = task.id
        doc.save(update_fields=["celery_task_id"])
        
        return Response(
            DocumentSerializer(doc).data,
            status=status.HTTP_202_ACCEPTED,
        )


class DocumentCancelView(APIView):
    """Cancela o processamento de um documento."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        qs = Document.objects.all() if user.role == "admin" else Document.objects.filter(uploaded_by=user)
        
        try:
            doc = qs.get(pk=pk)
        except Document.DoesNotExist:
            return Response({"detail": "Documento não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
        # Só pode cancelar se estiver processando
        if doc.status not in [Document.Status.PENDING, Document.Status.PROCESSING]:
            return Response(
                {"detail": "Documento não está em processamento."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Tentar revogar a task do Celery
        if doc.celery_task_id:
            celery_app.control.revoke(doc.celery_task_id, terminate=True, signal='SIGTERM')
        
        # Atualizar status
        doc.status = Document.Status.CANCELLED
        doc.error_message = "Processamento cancelado pelo usuário"
        doc.progress_message = "Cancelado"
        doc.save(update_fields=["status", "error_message", "progress_message", "updated_at"])
        
        log_action(
            request.user,
            "DOCUMENT_CANCEL",
            f'Processamento do documento "{doc.original_filename}" foi cancelado',
            request,
        )
        
        return Response(
            DocumentSerializer(doc).data,
            status=status.HTTP_200_OK,
        )
