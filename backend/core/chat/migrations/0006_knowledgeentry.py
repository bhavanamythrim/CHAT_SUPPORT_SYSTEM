from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_chatroom_is_closed'),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(choices=[('post_office', 'Post Office'), ('water_board', 'Water Board'), ('electricity_board', 'Electricity Board'), ('municipality', 'Municipality'), ('general', 'General Help Desk')], default='general', max_length=40)),
                ('intent', models.CharField(blank=True, default='', max_length=60)),
                ('trigger_keywords', models.CharField(blank=True, default='', help_text='Comma-separated keywords used to match user messages.', max_length=300)),
                ('question', models.CharField(max_length=255)),
                ('answer', models.TextField()),
                ('priority', models.PositiveIntegerField(default=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('priority', 'id'),
            },
        ),
    ]
