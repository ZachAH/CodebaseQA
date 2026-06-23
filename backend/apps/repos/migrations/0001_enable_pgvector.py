from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    """Enable the pgvector extension before any vector columns are created."""

    initial = True

    dependencies = []

    operations = [
        VectorExtension(),
    ]
