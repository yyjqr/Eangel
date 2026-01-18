from django.db import models


class TechNews(models.Model):
    id = models.AutoField(primary_key=True, db_column="Id")
    rate = models.FloatField(db_column="Rate")
    title = models.CharField(max_length=500, db_column="title")
    author = models.CharField(max_length=100, db_column="author")
    publish_time = models.CharField(max_length=100, db_column="publish_time")
    content = models.TextField(db_column="content")
    url = models.CharField(max_length=500, db_column="url")
    key_word = models.CharField(max_length=100, db_column="key_word")
    category = models.CharField(max_length=50, db_column="category", default="科技")
    image_url = models.CharField(
        max_length=500, db_column="image_url", default="", blank=True
    )

    class Meta:
        db_table = "techTB"
        managed = False

    def __str__(self):
        return self.title


class UserComment(models.Model):
    """用户评论建议模型"""

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, verbose_name="用户名", default="匿名")
    email = models.EmailField(max_length=200, verbose_name="邮箱", blank=True)
    comment = models.TextField(verbose_name="评论内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    is_approved = models.BooleanField(default=True, verbose_name="已审核")

    class Meta:
        db_table = "user_comments"
        ordering = ["-created_at"]
        verbose_name = "用户评论"
        verbose_name_plural = "用户评论"

    def __str__(self):
        return f"{self.username}: {self.comment[:50]}"
