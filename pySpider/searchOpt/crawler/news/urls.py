from django.urls import path
from . import views

urlpatterns = [
    path("", views.news_list, name="news_list"),
    path("submit-comment/", views.submit_comment, name="submit_comment"),
]
