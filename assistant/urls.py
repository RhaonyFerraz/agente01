from django.urls import path
from . import views

urlpatterns = [
    # PWA Endpoints
    path('', views.index_view, name='pwa_home'),
    path('manifest.json', views.manifest_view, name='pwa_manifest'),
    path('sw.js', views.service_worker_view, name='pwa_service_worker'),
    
    # REST API - Briefing
    path('api/briefing/today/', views.api_today_briefing, name='api_today_briefing'),
    path('api/briefing/generate/', views.api_refresh_briefing, name='api_refresh_briefing'),
    
    # REST API - Temas
    path('api/themes/', views.api_themes_list, name='api_themes_list'),
    path('api/themes/select/', views.api_theme_select, name='api_theme_select'),
    
    # REST API - Agenda e E-mails
    path('api/calendar/', views.api_events_view, name='api_calendar'),
    path('api/emails/', views.api_emails_view, name='api_emails'),
    
    # REST API - Configurações
    path('api/settings/', views.api_settings_view, name='api_settings'),
    
    # REST API - Chat IA
    path('api/chat/messages/', views.api_chat_messages, name='api_chat_messages'),
    path('api/chat/send/', views.api_chat_send, name='api_chat_send'),
    
    # REST API - Notificações
    path('api/notifications/telegram/send/', views.api_send_telegram, name='api_send_telegram'),
    path('api/notifications/telegram/test/', views.api_test_telegram, name='api_test_telegram'),
    path('api/notifications/whatsapp/text/', views.api_whatsapp_share_text, name='api_whatsapp_share_text'),
    
    # NOVOS: Múltiplas Cotações, Previsão Semanal e Tarefas Rápidas
    path('api/currency/multi/', views.api_multi_currency, name='api_multi_currency'),
    path('api/weather/weekly/', views.api_weekly_forecast, name='api_weekly_forecast'),
    path('api/tasks/', views.api_tasks_list, name='api_tasks_list'),
    path('api/tasks/<int:task_id>/', views.api_task_detail, name='api_task_detail'),
    
    # REST API - Nuvem de Dados (Supabase / PostgreSQL)
    path('api/cloud-db/status/', views.api_cloud_db_status, name='api_cloud_db_status'),
    path('api/cloud-db/test/', views.api_cloud_db_test, name='api_cloud_db_test'),
    path('api/cloud-db/save/', views.api_cloud_db_save, name='api_cloud_db_save'),
    path('api/cloud-db/export/', views.api_cloud_db_export, name='api_cloud_db_export'),
    path('api/cloud-db/import/', views.api_cloud_db_import, name='api_cloud_db_import'),

    # REST API - Síntese Vocal Neural (Edge-TTS)
    path('api/voice/tts/', views.api_voice_tts, name='api_voice_tts'),
]
