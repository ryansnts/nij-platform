from django.urls import path
from .views import (
    AnalysisResultDetailView,
    BCBSeriesListView,
    BCBSeriesDataView,
    INPCFactorsView,
    INPCSeriesView,
)

urlpatterns = [
    path("<uuid:document_id>/", AnalysisResultDetailView.as_view(), name="analysis-detail"),
    # Endpoints do Banco Central
    path("bcb/series/", BCBSeriesListView.as_view(), name="bcb-series-list"),
    path("bcb/series/data/", BCBSeriesDataView.as_view(), name="bcb-series-data"),
    path("bcb/inpc/", INPCSeriesView.as_view(), name="bcb-inpc-series"),
    path("bcb/inpc/fatores/", INPCFactorsView.as_view(), name="bcb-inpc-fatores"),
]
