from django.contrib import admin
from .models import TechNews, UserComment, HotProduct, DailyStats, UserIPLog, OriginalArticle


@admin.register(UserComment)
class UserCommentAdmin(admin.ModelAdmin):
    list_display = ['username', 'comment_preview', 'created_at', 'is_approved']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['username', 'email', 'comment']
    list_editable = ['is_approved']
    ordering = ['-created_at']

    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = '评论内容'


@admin.register(HotProduct)
class HotProductAdmin(admin.ModelAdmin):
    list_display = ['rank', 'title_preview', 'category', 'rate', 'period_type', 'period_start', 'updated_at']
    list_filter = ['period_type', 'category', 'period_start']
    search_fields = ['title', 'category']
    ordering = ['-period_start', 'rank']
    readonly_fields = ['created_at', 'updated_at']

    def title_preview(self, obj):
        return obj.title[:60] + '...' if len(obj.title) > 60 else obj.title
    title_preview.short_description = '产品标题'


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ['date', 'unique_visitors', 'total_views']
    list_filter = ['date']
    ordering = ['-date']
    readonly_fields = ['date']


@admin.register(UserIPLog)
class UserIPLogAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'visit_date', 'created_at']
    list_filter = ['visit_date']
    search_fields = ['ip_address']
    ordering = ['-created_at']
    readonly_fields = ['ip_address', 'visit_date', 'created_at']


@admin.register(OriginalArticle)
class OriginalArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'source_type', 'category', 'is_published', 'created_at']
    list_filter = ['source_type', 'category', 'is_published']
    search_fields = ['title', 'author', 'content']
    list_editable = ['is_published']
    ordering = ['-created_at']
