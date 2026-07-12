from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0007_aisearchtask_result_payload'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE user_comments DEFAULT CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='usercomment',
            name='username',
            field=models.CharField(
                db_collation='utf8mb4_unicode_ci',
                default='匿名',
                max_length=100,
                verbose_name='用户名',
            ),
        ),
        migrations.AlterField(
            model_name='usercomment',
            name='email',
            field=models.EmailField(
                blank=True,
                db_collation='utf8mb4_unicode_ci',
                max_length=200,
                verbose_name='邮箱',
            ),
        ),
        migrations.AlterField(
            model_name='usercomment',
            name='comment',
            field=models.TextField(db_collation='utf8mb4_unicode_ci', verbose_name='评论内容'),
        ),
    ]
