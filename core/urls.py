from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile_setup, name='profile_setup'),
    path('resume/', views.resume_upload, name='resume_upload'),
    path('chat/', views.chat, name='chat'),
    path('chat/<int:conversation_id>/', views.chat, name='chat_conversation'),
    path('chat/new/', views.new_conversation, name='new_conversation'),
    path('chat/<int:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
    path('api/chat/send/', views.send_message, name='send_message'),
]
