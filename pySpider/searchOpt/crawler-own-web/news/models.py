from django.db import models

class TechNews(models.Model):
    id = models.AutoField(primary_key=True, db_column='Id')
    rate = models.FloatField(db_column='Rate')
    title = models.CharField(max_length=500, db_column='title')
    author = models.CharField(max_length=100, db_column='author')
    publish_time = models.CharField(max_length=100, db_column='publish_time')
    content = models.TextField(db_column='content')
    url = models.CharField(max_length=500, db_column='url')
    key_word = models.CharField(max_length=100, db_column='key_word')
    category = models.CharField(max_length=50, db_column='category', default='科技')
    image_url = models.CharField(max_length=500, db_column='image_url', default='', blank=True)

    class Meta:
        db_table = 'techTB'
        managed = False

    def __str__(self):
        return self.title


class FeaturedSelection(models.Model):
    """精选资讯历史快照"""
    selection_date = models.DateField(verbose_name='精选日期')
    slot_order = models.PositiveSmallIntegerField(verbose_name='展示顺序')
    selection_mode = models.CharField(max_length=32, default='tech4-econ2-mil2', verbose_name='精选模式')
    news_id = models.IntegerField(null=True, blank=True, verbose_name='原新闻ID')
    title = models.CharField(max_length=500, verbose_name='标题')
    url = models.CharField(max_length=500, verbose_name='链接')
    category = models.CharField(max_length=50, verbose_name='分类')
    rate = models.FloatField(verbose_name='原始权重')
    selection_score = models.FloatField(default=0, verbose_name='统一展示分')
    image_url = models.CharField(max_length=500, default='', blank=True, verbose_name='图片链接')
    content = models.TextField(blank=True, default='', verbose_name='摘要内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'featured_selections'
        verbose_name = '精选资讯快照'
        verbose_name_plural = '精选资讯快照'
        ordering = ['-selection_date', 'slot_order']
        constraints = [
            models.UniqueConstraint(fields=['selection_date', 'slot_order'], name='uniq_featured_selection_slot'),
        ]
        indexes = [
            models.Index(fields=['selection_date', 'selection_mode']),
            models.Index(fields=['category', 'selection_date']),
        ]

    def __str__(self):
        return f"{self.selection_date} #{self.slot_order} {self.title}"


class UserComment(models.Model):
    """用户评论建议模型"""
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, verbose_name='用户名', default='匿名')
    email = models.EmailField(max_length=200, verbose_name='邮箱', blank=True)
    comment = models.TextField(verbose_name='评论内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    is_approved = models.BooleanField(default=True, verbose_name='已审核')

    class Meta:
        db_table = 'user_comments'
        ordering = ['-created_at']
        verbose_name = '用户评论'
        verbose_name_plural = '用户评论'

    def __str__(self):
        return f"{self.username}: {self.comment[:50]}"


class DailyStats(models.Model):
    """每日访问统计"""
    date = models.DateField(unique=True, verbose_name='日期')
    total_views = models.IntegerField(default=0, verbose_name='总页面浏览量(PV)')
    unique_visitors = models.IntegerField(default=0, verbose_name='独立访客数(UV)')

    class Meta:
        db_table = 'daily_stats'
        verbose_name = '每日统计'
        verbose_name_plural = '每日统计'
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}: UV={self.unique_visitors}, PV={self.total_views}"

class UserIPLog(models.Model):
    """用户IP访问日志"""
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    visit_date = models.DateField(verbose_name='访问日期', auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='访问时间')

    class Meta:
        db_table = 'user_ip_logs'
        verbose_name = 'IP日志'
        verbose_name_plural = 'IP日志'
        # 联合索引，加速查询当日某IP是否存在
        indexes = [
            models.Index(fields=['visit_date', 'ip_address']),
        ]

    def __str__(self):
        return f"{self.visit_date} - {self.ip_address}"


class HotProduct(models.Model):
    """热点产品排名"""
    title = models.CharField(max_length=500, verbose_name='产品标题')
    url = models.CharField(max_length=500, verbose_name='链接')
    category = models.CharField(max_length=50, verbose_name='产品类别')
    rate = models.FloatField(verbose_name='权重评分')
    image_url = models.CharField(max_length=500, verbose_name='图片链接', blank=True, default='')
    source = models.CharField(max_length=100, verbose_name='来源', blank=True)
    rank = models.IntegerField(verbose_name='排名', default=0)
    period_type = models.CharField(max_length=20, verbose_name='统计周期', choices=[
        ('daily', '每日'),
        ('weekly', '每周'),
        ('monthly', '每月')
    ], default='weekly')
    period_start = models.DateField(verbose_name='周期开始日期')
    period_end = models.DateField(verbose_name='周期结束日期')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'hot_products'
        verbose_name = '热点产品'
        verbose_name_plural = '热点产品'
        ordering = ['-period_start', 'rank']
        indexes = [
            models.Index(fields=['period_type', 'period_start']),
            models.Index(fields=['category', 'period_start']),
        ]

    def __str__(self):
        return f"[{self.period_type}] Rank {self.rank}: {self.title}"


class AiSearchTask(models.Model):
    """AI 全网搜索任务（无 Celery，threading 异步执行）"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '抓取中'),
        ('done', '完成'),
        ('error', '失败'),
    ]
    CATEGORY_CHOICES = [
        ('all', '全部'),
        ('tech', '科技'),
        ('economy', '经济'),
        ('product', '产品'),
        ('military', '军事'),
        ('design', '设计'),
        ('science', '科学'),
    ]

    query = models.CharField(max_length=200, verbose_name='搜索关键词')
    target_url = models.CharField(max_length=500, blank=True, default='', verbose_name='目标URL')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='all', verbose_name='分类')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='任务状态')
    result_md = models.TextField(blank=True, default='', verbose_name='抓取结果')
    result_payload = models.TextField(blank=True, default='', verbose_name='结构化结果')
    error_msg = models.CharField(max_length=500, blank=True, default='', verbose_name='错误信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ai_search_tasks'
        verbose_name = 'AI搜索任务'
        verbose_name_plural = 'AI搜索任务'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.status}] {self.query}"


class OriginalArticle(models.Model):
    """原创专栏文章（自己写的、微信文章等）"""
    SOURCE_CHOICES = [
        ('original', '原创'),
        ('wechat', '微信公众号'),
        ('reprint', '转载'),
    ]
    title = models.CharField(max_length=500, verbose_name='标题')
    author = models.CharField(max_length=100, verbose_name='作者', default='编辑部')
    content = models.TextField(verbose_name='正文内容', help_text='支持 Markdown 或纯文本')
    summary = models.CharField(max_length=500, verbose_name='摘要', blank=True)
    url = models.CharField(max_length=500, verbose_name='原文链接', blank=True, help_text='微信文章或外部链接')
    image_url = models.CharField(max_length=500, verbose_name='封面图片', blank=True, default='')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='original', verbose_name='来源类型')
    category = models.CharField(max_length=50, verbose_name='分类', default='原创')
    is_published = models.BooleanField(default=True, verbose_name='是否发布')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'original_articles'
        verbose_name = '原创文章'
        verbose_name_plural = '原创文章'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_source_type_display()}] {self.title}"
