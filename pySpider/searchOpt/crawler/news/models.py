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

    class Meta:
        db_table = "techTB"
        managed = False

    def __str__(self):
        return self.title
