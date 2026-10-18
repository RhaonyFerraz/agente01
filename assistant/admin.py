from django.contrib import admin
from .models import Theme, UserPreference, CalendarEvent, EmailHighlight, DailyBriefing, ChatMessage, QuickTask

@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'is_default', 'primary_color', 'accent_color')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('city_name', 'latitude', 'longitude', 'active_theme', 'enable_voice', 'daily_briefing_time', 'updated_at')


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'category', 'is_important', 'location')
    list_filter = ('category', 'is_important', 'start_time')
    search_fields = ('title', 'description', 'location')


@admin.register(EmailHighlight)
class EmailHighlightAdmin(admin.ModelAdmin):
    list_display = ('sender', 'subject', 'received_at', 'is_important', 'action_required', 'is_read')
    list_filter = ('is_important', 'action_required', 'is_read')
    search_fields = ('sender', 'subject', 'snippet')


@admin.register(DailyBriefing)
class DailyBriefingAdmin(admin.ModelAdmin):
    list_display = ('date', 'weather_city', 'weather_temp_min', 'weather_temp_max', 'usd_bid', 'created_at')
    list_filter = ('date', 'weather_city')
    readonly_fields = ('created_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('role', 'content_preview', 'action_type', 'created_at')
    list_filter = ('role', 'action_type', 'created_at')
    search_fields = ('content', 'action_type')

    def content_preview(self, obj):
        return obj.content[:50]
    content_preview.short_description = "Conteúdo"


@admin.register(QuickTask)
class QuickTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'priority', 'category', 'is_done', 'due_date', 'created_at')
    list_filter = ('priority', 'category', 'is_done', 'due_date')
    search_fields = ('title', 'notes')
    list_editable = ('is_done',)
    date_hierarchy = 'due_date'
