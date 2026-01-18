from django.contrib import admin
from .models import TechNews, UserComment


@admin.register(UserComment)
class UserCommentAdmin(admin.ModelAdmin):
    list_display = ["username", "comment_preview", "created_at", "is_approved"]
    list_filter = ["is_approved", "created_at"]
    search_fields = ["username", "email", "comment"]
    list_editable = ["is_approved"]
    ordering = ["-created_at"]

    def comment_preview(self, obj):
        return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment

    comment_preview.short_description = "评论内容"
