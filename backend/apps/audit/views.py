from rest_framework import generics, permissions
from .models import AuditLog
from .serializers import AuditLogSerializer


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user").all()
        action = self.request.query_params.get("action")
        username = self.request.query_params.get("username")
        if action:
            qs = qs.filter(action__icontains=action)
        if username:
            qs = qs.filter(username__icontains=username)
        return qs
