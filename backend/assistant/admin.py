from django.contrib import admin

from .models import PendingAction


@admin.register(PendingAction)
class PendingActionAdmin(admin.ModelAdmin):
    list_display = ("id", "action_type", "title", "status", "created_at")
    list_filter = ("status", "action_type")
    search_fields = ("title", "summary")
