# Generated 2026-03-21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0004_featuredselection"),
    ]

    operations = [
        migrations.CreateModel(
            name="AiSearchTask",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("query", models.CharField(max_length=200, verbose_name="搜索关键词")),
                (
                    "target_url",
                    models.CharField(
                        blank=True, default="", max_length=500, verbose_name="目标URL"
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("all", "全部"),
                            ("tech", "科技"),
                            ("economy", "经济"),
                            ("product", "产品"),
                            ("military", "军事"),
                            ("design", "设计"),
                            ("science", "科学"),
                        ],
                        default="all",
                        max_length=20,
                        verbose_name="分类",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "等待中"),
                            ("running", "抓取中"),
                            ("done", "完成"),
                            ("error", "失败"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="任务状态",
                    ),
                ),
                (
                    "result_md",
                    models.TextField(blank=True, default="", verbose_name="抓取结果"),
                ),
                (
                    "error_msg",
                    models.CharField(
                        blank=True, default="", max_length=500, verbose_name="错误信息"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
            ],
            options={
                "verbose_name": "AI搜索任务",
                "verbose_name_plural": "AI搜索任务",
                "db_table": "ai_search_tasks",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="aisearchtask",
            index=models.Index(
                fields=["status", "created_at"], name="ai_search_tasks_status_idx"
            ),
        ),
    ]
