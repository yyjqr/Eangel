from django.urls import path
from . import views

urlpatterns = [
    path('', views.news_list, name='news_list'),
    path('articles/<int:article_id>/', views.original_article_detail, name='original_article_detail'),
    path('submit-comment/', views.submit_comment, name='submit_comment'),
    path('ai-search/', views.ai_search_submit, name='ai_search_submit'),
    path('ai-search/status/<int:task_id>/', views.ai_search_status, name='ai_search_status'),
]
