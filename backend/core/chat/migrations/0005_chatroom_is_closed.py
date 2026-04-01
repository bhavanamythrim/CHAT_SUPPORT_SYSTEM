from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_message_is_read'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatroom',
            name='is_closed',
            field=models.BooleanField(default=False),
        ),
    ]
