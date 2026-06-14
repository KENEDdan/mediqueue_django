from django.urls import path
from . import views

urlpatterns = [
    path('bell/',           views.notification_bell_data,  name='notification_bell_data'),
    path('all/',            views.notification_list,       name='notification_list'),
    path('<int:pk>/read/',  views.mark_notification_read,   name='mark_notification_read'),
    path('mark-all-read/',  views.mark_all_read,            name='mark_all_read'),
    # urls.py
    path('ai-chat/', views.ai_chat, name='ai_chat'),
]