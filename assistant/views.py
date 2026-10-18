import json
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Theme, UserPreference, CalendarEvent, EmailHighlight, DailyBriefing, ChatMessage
from .services import (
    BriefingOrchestrator, WeatherService, CurrencyService, 
    GeminiService, ChatAssistantService, NotificationService, NeuralVoiceService
)

def index_view(request):
    """Renderiza a aplicação PWA principal"""
    active_theme = Theme.objects.filter(is_default=True).first()
    pref = UserPreference.objects.first()
    if pref and pref.active_theme:
        active_theme = pref.active_theme
        
    context = {
        "theme": active_theme,
        "app_title": "Assistente Pessoal IA",
    }
    response = render(request, "index.html", context)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def manifest_view(request):
    """Retorna o Web App Manifest do PWA"""
    active_theme = Theme.objects.filter(is_default=True).first()
    theme_color = active_theme.primary_color if active_theme else "#6366f1"
    bg_color = active_theme.bg_gradient_start if active_theme else "#0f172a"
    
    manifest_data = {
        "name": "Bella - Assistente Pessoal Inteligente",
        "short_name": "Bella IA",
        "description": "Bella: sua assistente pessoal inteligente com voz jovem, agenda, e-mails, clima e IA Gemini.",
        "start_url": "/",
        "display": "standalone",
        "background_color": bg_color,
        "theme_color": theme_color,
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JsonResponse(manifest_data)


def service_worker_view(request):
    """Entrega o Service Worker com headers adequados e estratégia Network-First para atualizações rápidas"""
    sw_code = """// Service Worker da Bella PWA
const CACHE_NAME = 'bella-pwa-v7';
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/static/css/styles.css',
  '/static/js/app.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Estratégia Network First para garantir que atualizações de código, navegação e APIs sejam imediatas
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // Apenas faz cache de respostas bem sucedidas
        if (networkResponse && networkResponse.status === 200) {
          const resClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone));
        }
        return networkResponse;
      })
      .catch(() => caches.match(event.request))
  );
});
"""
    response = HttpResponse(sw_code, content_type="application/javascript")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# =========================================================================
# REST API Endpoints
# =========================================================================

def parse_json_body(request):
    """Auxiliar para decodificar JSON do corpo da requisição com tolerância a encodings"""
    try:
        raw = request.body.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        raw = request.body.decode('latin-1', errors='replace')
    return json.loads(raw)


def api_today_briefing(request):
    """GET /api/briefing/today/ - Retorna todos os dados do briefing do dia"""
    data = BriefingOrchestrator.get_today_briefing(force_refresh=False)
    
    # Adiciona tema ativo atual
    pref = UserPreference.objects.first()
    theme = pref.active_theme if pref and pref.active_theme else Theme.objects.filter(is_default=True).first()
    
    data["theme"] = {
        "name": theme.name if theme else "Modern Glass",
        "slug": theme.slug if theme else "modern-glass",
        "primary_color": theme.primary_color if theme else "#6366f1",
        "secondary_color": theme.secondary_color if theme else "#8b5cf6",
        "accent_color": theme.accent_color if theme else "#10b981",
        "bg_gradient_start": theme.bg_gradient_start if theme else "#0f172a",
        "bg_gradient_end": theme.bg_gradient_end if theme else "#1e1b4b",
        "card_bg": theme.card_bg if theme else "rgba(30, 41, 59, 0.75)",
        "card_border": theme.card_border if theme else "rgba(255, 255, 255, 0.12)",
        "text_color": theme.text_color if theme else "#f8fafc",
        "text_muted": theme.text_muted if theme else "#94a3b8",
        "font_family": theme.font_family if theme else "'Inter', sans-serif"
    } if theme else {}

    return JsonResponse(data)


@csrf_exempt
def api_refresh_briefing(request):
    """POST /api/briefing/generate/ - Força nova geração com o Gemini"""
    if request.method == "POST":
        data = BriefingOrchestrator.get_today_briefing(force_refresh=True)
        return JsonResponse({"status": "success", "data": data})
    return JsonResponse({"error": "Método não permitido"}, status=405)


def api_themes_list(request):
    """GET /api/themes/ - Lista os temas disponíveis cadastrados no Django"""
    themes = Theme.objects.filter(is_active=True)
    pref = UserPreference.objects.first()
    active_id = pref.active_theme.id if pref and pref.active_theme else None

    theme_list = [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "description": t.description,
            "is_default": t.is_default,
            "is_selected": (t.id == active_id) if active_id else t.is_default,
            "primary_color": t.primary_color,
            "secondary_color": t.secondary_color,
            "accent_color": t.accent_color,
            "bg_gradient_start": t.bg_gradient_start,
            "bg_gradient_end": t.bg_gradient_end,
            "card_bg": t.card_bg,
            "card_border": t.card_border,
            "text_color": t.text_color,
            "text_muted": t.text_muted,
            "font_family": t.font_family
        }
        for t in themes
    ]
    return JsonResponse({"themes": theme_list})


@csrf_exempt
def api_theme_select(request):
    """POST /api/themes/select/ - Altera o tema ativo do usuário"""
    if request.method == "POST":
        try:
            body = parse_json_body(request)
            theme_id = body.get("theme_id")
            theme = Theme.objects.get(id=theme_id)
            
            pref, _ = UserPreference.objects.get_or_create(id=1)
            pref.active_theme = theme
            pref.save()
            
            return JsonResponse({"status": "success", "active_theme": theme.name})
        except Theme.DoesNotExist:
            return JsonResponse({"error": "Tema não encontrado"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def api_events_view(request):
    """GET ou POST para eventos de agenda"""
    if request.method == "GET":
        events = CalendarEvent.objects.all().order_by('start_time')
        return JsonResponse({
            "events": [
                {
                    "id": ev.id,
                    "title": ev.title,
                    "description": ev.description,
                    "start_time": ev.start_time.strftime("%d/%m %H:%M"),
                    "start_time_iso": ev.start_time.isoformat(),
                    "location": ev.location,
                    "category": ev.category,
                    "category_label": ev.get_category_display(),
                    "is_important": ev.is_important
                }
                for ev in events
            ]
        })
    elif request.method == "POST":
        try:
            body = parse_json_body(request)
            title = body.get("title")
            start_str = body.get("start_time") # ISO ou YYYY-MM-DDTHH:MM
            category = body.get("category", "work")
            location = body.get("location", "")
            description = body.get("description", "")
            is_important = body.get("is_important", False)
            
            if not title or not start_str:
                return JsonResponse({"error": "Título e data/hora são obrigatórios"}, status=400)
                
            start_dt = timezone.datetime.fromisoformat(start_str)
            if timezone.is_naive(start_dt):
                start_dt = timezone.make_aware(start_dt)
                
            ev = CalendarEvent.objects.create(
                title=title,
                start_time=start_dt,
                category=category,
                location=location,
                description=description,
                is_important=is_important
            )
            return JsonResponse({"status": "created", "id": ev.id, "title": ev.title})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def api_emails_view(request):
    """GET ou POST para destaques de e-mails"""
    if request.method == "GET":
        emails = EmailHighlight.objects.all().order_by('-received_at')
        return JsonResponse({
            "emails": [
                {
                    "id": em.id,
                    "sender": em.sender,
                    "sender_email": em.sender_email,
                    "subject": em.subject,
                    "snippet": em.snippet,
                    "received_at": em.received_at.strftime("%d/%m %H:%M"),
                    "is_important": em.is_important,
                    "is_read": em.is_read,
                    "action_required": em.action_required
                }
                for em in emails
            ]
        })
    elif request.method == "POST":
        try:
            body = parse_json_body(request)
            sender = body.get("sender")
            subject = body.get("subject")
            snippet = body.get("snippet", "")
            is_important = body.get("is_important", False)
            action_required = body.get("action_required", False)
            
            if not sender or not subject:
                return JsonResponse({"error": "Remetente e Assunto são obrigatórios"}, status=400)
                
            em = EmailHighlight.objects.create(
                sender=sender,
                subject=subject,
                snippet=snippet,
                is_important=is_important,
                action_required=action_required,
                received_at=timezone.now()
            )
            return JsonResponse({"status": "created", "id": em.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def api_settings_view(request):
    """GET ou POST para preferências gerais do sistema (chave Gemini, Cidade, Telegram, WhatsApp)"""
    pref, _ = UserPreference.objects.get_or_create(id=1)
    
    if request.method == "GET":
        has_env_key = bool(settings.GEMINI_API_KEY)
        has_custom_key = bool(pref.gemini_api_key)
        
        return JsonResponse({
            "city_name": pref.city_name,
            "latitude": float(pref.latitude),
            "longitude": float(pref.longitude),
            "has_gemini_key": has_env_key or has_custom_key,
            "enable_voice": pref.enable_voice,
            "briefing_hour": pref.daily_briefing_time.strftime("%H:%M"),
            "telegram_bot_token": pref.telegram_bot_token or "",
            "telegram_chat_id": pref.telegram_chat_id or "",
            "whatsapp_number": pref.whatsapp_number or "",
            "auto_send_telegram": pref.auto_send_telegram
        })
    elif request.method == "POST":
        try:
            body = parse_json_body(request)
            if "city_name" in body:
                pref.city_name = body["city_name"]
            if "latitude" in body and "longitude" in body:
                pref.latitude = body["latitude"]
                pref.longitude = body["longitude"]
            if "gemini_api_key" in body:
                pref.gemini_api_key = body["gemini_api_key"].strip()
            if "enable_voice" in body:
                pref.enable_voice = bool(body["enable_voice"])
            if "telegram_bot_token" in body:
                pref.telegram_bot_token = body["telegram_bot_token"].strip()
            if "telegram_chat_id" in body:
                pref.telegram_chat_id = body["telegram_chat_id"].strip()
            if "whatsapp_number" in body:
                pref.whatsapp_number = body["whatsapp_number"].strip()
            if "auto_send_telegram" in body:
                pref.auto_send_telegram = bool(body["auto_send_telegram"])
            pref.save()
            return JsonResponse({"status": "updated"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"error": "Método não permitido"}, status=405)


def api_chat_messages(request):
    """GET /api/chat/messages/ - Retorna histórico recente de mensagens do chat"""
    messages = ChatMessage.objects.all().order_by('created_at')[:30]
    return JsonResponse({
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "action_type": m.action_type,
                "created_at": timezone.localtime(m.created_at).strftime("%H:%M")
            }
            for m in messages
        ]
    })


@csrf_exempt
def api_chat_send(request):
    """POST /api/chat/send/ - Processa mensagem de voz ou texto e executa ações com o Gemini"""
    if request.method == "POST":
        try:
            body = parse_json_body(request)
            message = body.get("message", "").strip()
            if not message:
                return JsonResponse({"error": "Mensagem vazia"}, status=400)

            result = ChatAssistantService.process_message(message)
            return JsonResponse({"status": "success", "result": result})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def api_send_telegram(request):
    """POST /api/notifications/telegram/send/ - Envia o resumo matinal atual para o Telegram"""
    if request.method == "POST":
        result = NotificationService.send_daily_briefing_telegram()
        return JsonResponse(result)
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def api_test_telegram(request):
    """POST /api/notifications/telegram/test/ - Testa as credenciais do Telegram"""
    if request.method == "POST":
        try:
            body = parse_json_body(request)
            token = body.get("bot_token")
            chat_id = body.get("chat_id")
            
            if not token or not chat_id:
                pref = UserPreference.objects.first()
                token = token or (pref.telegram_bot_token if pref else None)
                chat_id = chat_id or (pref.telegram_chat_id if pref else None)
                
            result = NotificationService.test_telegram_connection(token, chat_id)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"error": "Método não permitido"}, status=405)


def api_whatsapp_share_text(request):
    """GET /api/notifications/whatsapp/text/ - Retorna texto formatado para compartilhar no WhatsApp"""
    data = BriefingOrchestrator.get_today_briefing()
    pref = UserPreference.objects.first()
    phone = pref.whatsapp_number if pref and pref.whatsapp_number else ""
    
    text = NotificationService.format_whatsapp_share_text(data)
    import urllib.parse
    encoded_text = urllib.parse.quote(text)
    
    # Se houver número configurado, direciona para o número específico, senão abre o seletor geral
    if phone:
        clean_phone = "".join(filter(str.isdigit, phone))
        url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
    else:
        url = f"https://api.whatsapp.com/send?text={encoded_text}"
        
    return JsonResponse({"url": url, "text": text})


# =========================================================================
# NOVOS ENDPOINTS: Cotações Múltiplas, Previsão Semanal e Tarefas Rápidas
# =========================================================================

def api_multi_currency(request):
    """GET /api/currency/multi/ - Retorna cotações de USD, EUR e BTC em BRL"""
    from .services import CurrencyService
    rates = CurrencyService.get_multi_rates()
    return JsonResponse({"rates": rates})


def api_weekly_forecast(request):
    """GET /api/weather/weekly/ - Retorna previsão de 7 dias para gráfico sparkline"""
    from .services import WeeklyForecastService
    pref = UserPreference.objects.first()
    lat = float(pref.latitude) if pref else settings.DEFAULT_LAT
    lon = float(pref.longitude) if pref else settings.DEFAULT_LON
    days = WeeklyForecastService.get_weekly(lat=lat, lon=lon)
    return JsonResponse({"forecast": days})


@csrf_exempt
def api_tasks_list(request):
    """GET /api/tasks/ - Lista tarefas do dia | POST - Cria nova tarefa"""
    from .models import QuickTask
    today = timezone.localdate()
    
    if request.method == "GET":
        tasks = QuickTask.objects.filter(due_date=today)
        return JsonResponse({
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "is_done": t.is_done,
                    "priority": t.priority,
                    "category": t.category,
                    "category_label": t.get_category_display(),
                    "notes": t.notes,
                    "created_at": timezone.localtime(t.created_at).strftime("%H:%M"),
                }
                for t in tasks
            ],
            "total": tasks.count(),
            "done": tasks.filter(is_done=True).count(),
        })
    
    if request.method == "POST":
        try:
            body = parse_json_body(request)
            task = QuickTask.objects.create(
                title=body.get("title", "Nova tarefa"),
                priority=body.get("priority", "medium"),
                category=body.get("category", "work"),
                notes=body.get("notes", ""),
                due_date=today,
            )
            return JsonResponse({
                "status": "created",
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "category": task.category,
                "category_label": task.get_category_display(),
                "is_done": task.is_done,
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def api_task_detail(request, task_id):
    """PATCH /api/tasks/<id>/ - Atualiza tarefa (marcar como feita) | DELETE - Remove"""
    from .models import QuickTask
    try:
        task = QuickTask.objects.get(id=task_id)
    except QuickTask.DoesNotExist:
        return JsonResponse({"error": "Tarefa não encontrada"}, status=404)
    
    if request.method == "PATCH":
        try:
            body = parse_json_body(request)
            if "is_done" in body:
                task.is_done = body["is_done"]
                task.completed_at = timezone.now() if body["is_done"] else None
            if "title" in body:
                task.title = body["title"]
            if "priority" in body:
                task.priority = body["priority"]
            task.save()
            return JsonResponse({"status": "updated", "id": task.id, "is_done": task.is_done})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        task.delete()
        return JsonResponse({"status": "deleted"})
    
    return JsonResponse({"error": "Método não permitido"}, status=405)




@csrf_exempt
def api_test_telegram(request):
    """POST /api/notifications/telegram/test/ - Testa as credenciais do Telegram"""
    if request.method == "POST":
        try:
            body = parse_json_body(request)
            token = body.get("bot_token")
            chat_id = body.get("chat_id")
            
            if not token or not chat_id:
                pref = UserPreference.objects.first()
                token = token or (pref.telegram_bot_token if pref else None)
                chat_id = chat_id or (pref.telegram_chat_id if pref else None)
                
            result = NotificationService.test_telegram_connection(token, chat_id)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"error": "Método não permitido"}, status=405)


def api_whatsapp_share_text(request):
    """GET /api/notifications/whatsapp/text/ - Retorna texto formatado para compartilhar no WhatsApp"""
    data = BriefingOrchestrator.get_today_briefing()
    pref = UserPreference.objects.first()
    phone = pref.whatsapp_number if pref and pref.whatsapp_number else ""
    
    text = NotificationService.format_whatsapp_share_text(data)
    import urllib.parse
    encoded_text = urllib.parse.quote(text)
    
    # Se houver número configurado, direciona para o número específico, senão abre o seletor geral
    if phone:
        clean_phone = "".join(filter(str.isdigit, phone))
        url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
    else:
        url = f"https://api.whatsapp.com/send?text={encoded_text}"
        
    return JsonResponse({"url": url, "text": text})


# =========================================================================
# BANCO DE DADOS NA NUVEM (SUPABASE / POSTGRESQL / FIREBASE)
# =========================================================================

def api_cloud_db_status(request):
    """GET /api/cloud-db/status/ - Retorna status do banco de dados (SQLite x Supabase)"""
    from .cloud_service import CloudDatabaseService
    status_info = CloudDatabaseService.get_status()
    return JsonResponse(status_info)


@csrf_exempt
def api_cloud_db_test(request):
    """POST /api/cloud-db/test/ - Testa conexão com DATABASE_URL informada"""
    if request.method == "POST":
        from .cloud_service import CloudDatabaseService
        try:
            body = parse_json_body(request)
            url_str = body.get("database_url", "").strip()
            res = CloudDatabaseService.test_connection_string(url_str)
            return JsonResponse(res)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def api_cloud_db_save(request):
    """POST /api/cloud-db/save/ - Salva a DATABASE_URL no .env"""
    if request.method == "POST":
        from .cloud_service import CloudDatabaseService
        try:
            body = parse_json_body(request)
            url_str = body.get("database_url", "").strip()
            if not url_str:
                return JsonResponse({"success": False, "error": "URL não pode ser vazia"}, status=400)

            # Primeiro testa a conexão
            test_res = CloudDatabaseService.test_connection_string(url_str)
            if not test_res.get("success"):
                return JsonResponse({"success": False, "error": f"Falha ao validar URL: {test_res.get('error')}"}, status=400)

            # Salva no .env
            CloudDatabaseService.save_cloud_url_to_env(url_str)
            return JsonResponse({
                "success": True,
                "message": f"DATABASE_URL salva com sucesso! Provedor: {test_res.get('provider')}. O servidor Django aplicará a conexão na nuvem."
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"error": "Método não permitido"}, status=405)


def api_cloud_db_export(request):
    """GET /api/cloud-db/export/ - Exporta todos os dados em formato JSON para download/backup"""
    from .cloud_service import CloudDatabaseService
    data = CloudDatabaseService.export_data_bundle()
    response = JsonResponse(data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="assistente_backup_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
    return response


@csrf_exempt
def api_cloud_db_import(request):
    """POST /api/cloud-db/import/ - Restaura registros a partir de um bundle JSON"""
    if request.method == "POST":
        from .cloud_service import CloudDatabaseService
        try:
            body = parse_json_body(request)
            counts = CloudDatabaseService.import_data_bundle(body)
            return JsonResponse({"success": True, "imported": counts})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def api_voice_tts(request):
    """GET ou POST /api/voice/tts/ - Gera áudio MP3 neural em tempo real com Edge-TTS"""
    try:
        if request.method == "POST":
            body = parse_json_body(request)
            text = body.get("text", "").strip()
            voice = body.get("voice", "thalita")
            rate = body.get("rate", "+0%")
            pitch = body.get("pitch", "+0Hz")
        else:
            text = request.GET.get("text", "").strip()
            voice = request.GET.get("voice", "thalita")
            rate = request.GET.get("rate", "+0%")
            pitch = request.GET.get("pitch", "+0Hz")

        if not text:
            return JsonResponse({"error": "Texto não fornecido para síntese vocal."}, status=400)

        # Limite máximo de segurança para uma única chamada de áudio
        if len(text) > 4000:
            text = text[:4000]

        audio_bytes = NeuralVoiceService.synthesize_to_mp3(text, voice_code=voice, rate=rate, pitch=pitch)
        
        response = HttpResponse(audio_bytes, content_type="audio/mpeg")
        response["Content-Disposition"] = 'inline; filename="bella_speech.mp3"'
        response["Cache-Control"] = "public, max-age=3600"
        return response
    except Exception as e:
        print(f"Erro ao gerar síntese vocal neural: {e}")
        return JsonResponse({"error": str(e)}, status=500)




