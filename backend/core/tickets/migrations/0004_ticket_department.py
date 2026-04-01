from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_ticket_assigned_to'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='department',
            field=models.CharField(
                choices=[
                    ('post_office', 'Post Office'),
                    ('water_board', 'Water Board'),
                    ('electricity_board', 'Electricity Board'),
                    ('municipality', 'Municipality'),
                    ('general', 'General Help Desk'),
                ],
                default='general',
                max_length=40,
            ),
        ),
    ]
