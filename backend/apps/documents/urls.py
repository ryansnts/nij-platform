from django.urls import path
from .views import DocumentUploadView, DocumentListView, DocumentDetailView, DocumentReprocessView, DocumentCancelView

urlpatterns = [
    path("", DocumentListView.as_view(), name="document-list"),
    path("upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<uuid:pk>/reprocess/", DocumentReprocessView.as_view(), name="document-reprocess"),
    path("<uuid:pk>/cancel/", DocumentCancelView.as_view(), name="document-cancel"),
]
