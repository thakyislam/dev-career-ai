from django.contrib import admin
from .models import UserProfile, Resume, Conversation, Message

admin.site.register(UserProfile)
admin.site.register(Resume)
admin.site.register(Conversation)
admin.site.register(Message)
