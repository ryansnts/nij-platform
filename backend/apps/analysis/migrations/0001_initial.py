from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalysisResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="analysis_result",
                    to="documents.document",
                )),
                ("nome", models.CharField(blank=True, max_length=255)),
                ("cpf", models.CharField(blank=True, max_length=20)),
                ("matricula", models.CharField(blank=True, max_length=50)),
                ("orgao", models.CharField(blank=True, max_length=255)),
                ("competencia", models.CharField(blank=True, max_length=10)),
                ("valor_bruto", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("valor_liquido", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("margem_consignavel", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("margem_utilizada", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("margem_disponivel", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("transacoes", models.JSONField(default=list)),
                ("contratos", models.JSONField(default=list)),
                ("descontos_indevidos", models.JSONField(default=list)),
                ("codigos_rmc", models.JSONField(default=list)),
                ("raw_text", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "analysis_results"},
        ),
    ]
