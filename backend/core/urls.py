from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
import os

# Pasta onde o frontend foi buildado
FRONTEND_DIST = os.path.join(settings.BASE_DIR, "static", "frontend")


# View para servir frontend
def frontend_index(request):
    from django.http import FileResponse

    index_file = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_file):
        return FileResponse(open(index_file, "rb"), content_type="text/html")
    return RedirectView.as_view(url="/login/")


def frontend_static(request, path):
    from django.http import FileResponse

    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, "rb"))
    return RedirectView.as_view(url="/login/")


urlpatterns = [
    path("", frontend_index),
    path("login/", frontend_index),
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/documents/", include("apps.documents.urls")),
    path("api/analysis/", include("apps.analysis.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/schema/", include("drf_spectacular.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
