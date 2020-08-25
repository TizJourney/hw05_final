# Generated by Django 2.2.9 on 2020-08-25 18:56

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0011_follow'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={'ordering': ('-created',)},
        ),
        migrations.RemoveField(
            model_name='comment',
            name='pub_date',
        ),
        migrations.AddField(
            model_name='comment',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, help_text='Время создания. По-умолчанию выставляется текущее время.', verbose_name='Время создания'),
            preserve_default=False,
        ),
    ]