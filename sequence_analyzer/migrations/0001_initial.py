# Generated by Django 5.0.2 on 2025-03-29 03:35

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SequenceSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence', models.CharField(max_length=130, validators=[django.core.validators.RegexValidator(code='invalid_sequence', message='Sequence must contain only valid amino acid letters (ACDEFGHIKLMNPQRSTVWY)', regex='^[ACDEFGHIKLMNPQRSTVWY]+$'), django.core.validators.MaxLengthValidator(130)])),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('done', 'Done')], default='pending', max_length=10)),
                ('submit_date', models.DateTimeField(auto_now_add=True)),
                ('result', models.FloatField(default=0)),
                ('result_date', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-submit_date'],
            },
        ),
    ]
