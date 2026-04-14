import uuid
import apps.documents.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(upload_to=apps.documents.models.upload_path)),
                ("original_filename", models.CharField(max_length=255)),
                ("file_size", models.PositiveIntegerField()),
                ("extraction_profile", models.CharField(
                    choices=[
                        ("auto", "Detecção Automática"),
                        ("contracheque", "Contracheque"),
                        ("inss_cartao", "Extrato INSS Cartão"),
                        ("fatura", "Fatura Cartão RMC"),
                        ("extrato_bancario", "Extrato Bancário"),
                        ("ficha_financeira_sead", "Ficha Financeira SEAD"),
                        ("historico_creditos_inss", "Histórico Créditos INSS"),
                    ],
                    default="auto", max_length=50,
                )),
                ("search_keywords", models.JSONField(blank=True, default=list)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pendente"), ("processing", "Processando"),
                        ("completed", "Concluído"), ("error", "Erro"),
                    ],
                    default="pending", max_length=20,
                )),
                ("error_message", models.TextField(blank=True)),
                ("uploaded_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="documents",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "documents", "ordering": ["-created_at"]},
        ),
    ]
