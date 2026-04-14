from rest_framework import serializers
from django.conf import settings
from .models import Document


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "file", "extraction_profile", "search_keywords"]

    def validate_file(self, value):
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Arquivo muito grande. Máximo: {settings.MAX_UPLOAD_SIZE_MB}MB."
            )
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Apenas arquivos PDF são aceitos.")
        return value

    def create(self, validated_data):
        validated_data["uploaded_by"] = self.context["request"].user
        validated_data["original_filename"] = validated_data["file"].name
        validated_data["file_size"] = validated_data["file"].size
        return super().create(validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    analysis = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "original_filename", "file_size", "extraction_profile",
            "search_keywords", "status", "error_message",
            "progress", "progress_message", "total_pages", "current_page",
            "uploaded_by_username", "created_at", "updated_at", "analysis",
        ]

    def get_analysis(self, obj):
        if hasattr(obj, "analysis_result"):
            from apps.analysis.serializers import AnalysisResultSerializer
            return AnalysisResultSerializer(obj.analysis_result).data
        return None
