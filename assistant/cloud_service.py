"""
Serviço de Nuvem de Dados para o Assistente Pessoal (Supabase / PostgreSQL / Firebase)
Gerencia conexão remota, migrações na nuvem e sincronização bidirecional de dados.
"""

import os
import json
import time
from django.db import connection, connections
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from .models import CalendarEvent, QuickTask, EmailHighlight, DailyBriefing, ChatMessage, UserPreference, Theme, VoiceMemo


class CloudDatabaseService:
    """Gerenciador de banco de dados na nuvem (Supabase / PostgreSQL)"""

    @staticmethod
    def get_status():
        """Retorna informações detalhadas sobre a base de dados ativa"""
        db_settings = settings.DATABASES['default']
        engine = db_settings.get('ENGINE', '')
        vendor = connection.vendor  # 'postgresql' ou 'sqlite'

        is_cloud = vendor == 'postgresql'
        host = db_settings.get('HOST', 'Localhost') or 'Local'
        name = db_settings.get('NAME', '')

        # Testa latência da conexão
        latency_ms = None
        try:
            start = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            latency_ms = round((time.time() - start) * 1000, 1)
            is_connected = True
        except Exception as e:
            is_connected = False
            connection_error = str(e)

        # Contagem de dados
        try:
            counts = {
                "events": CalendarEvent.objects.count(),
                "tasks": QuickTask.objects.count(),
                "emails": EmailHighlight.objects.count(),
                "briefings": DailyBriefing.objects.count(),
                "messages": ChatMessage.objects.count(),
            }
            total_records = sum(counts.values())
        except Exception:
            counts = {}
            total_records = 0

        # Identifica provedor
        provider = "SQLite (Local)"
        if is_cloud:
            host_str = str(host).lower()
            if "supabase" in host_str:
                provider = "Supabase PostgreSQL (Nuvem)"
            elif "neon" in host_str:
                provider = "Neon Serverless PostgreSQL (Nuvem)"
            elif "render" in host_str:
                provider = "Render PostgreSQL (Nuvem)"
            elif "railway" in host_str:
                provider = "Railway PostgreSQL (Nuvem)"
            else:
                provider = "PostgreSQL Remoto (Nuvem)"

        return {
            "is_cloud": is_cloud,
            "provider": provider,
            "vendor": vendor,
            "host": str(host),
            "database": str(name).split('/')[-1] if not is_cloud else str(name),
            "is_connected": is_connected,
            "latency_ms": latency_ms,
            "total_records": total_records,
            "counts": counts,
            "database_url_configured": bool(os.getenv('DATABASE_URL', '').strip()),
        }

    @staticmethod
    def test_connection_string(db_url):
        """Testa se uma URL de conexão PostgreSQL (ex: Supabase) é válida e acessível"""
        if not db_url or not db_url.strip():
            return {"success": False, "error": "A URL de conexão não foi informada."}

        url_str = db_url.strip()
        if not url_str.startswith(('postgres://', 'postgresql://')):
            return {"success": False, "error": "URL inválida. Deve iniciar com 'postgresql://' ou 'postgres://'."}

        try:
            import psycopg2
            start = time.time()
            # Tenta conectar via psycopg2 com timeout de 8 segundos
            conn = psycopg2.connect(url_str, connect_timeout=8)
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version_str = cur.fetchone()[0]
            cur.close()
            conn.close()
            latency = round((time.time() - start) * 1000, 1)

            provider_name = "PostgreSQL"
            if "supabase" in url_str.lower():
                provider_name = "Supabase PostgreSQL"
            elif "neon" in url_str.lower():
                provider_name = "Neon PostgreSQL"

            return {
                "success": True,
                "provider": provider_name,
                "version": version_str.split(',')[0],
                "latency_ms": latency,
                "message": f"Conexão bem-sucedida com {provider_name}! Latência: {latency}ms."
            }
        except Exception as e:
            err_msg = str(e)
            if "password authentication failed" in err_msg:
                err_msg = "Falha de autenticação: verifique se a senha informada na URL está correta."
            elif "timeout expired" in err_msg or "could not translate host" in err_msg:
                err_msg = "Tempo limite esgotado: verifique o host e sua conexão de internet."
            return {"success": False, "error": err_msg}

    @staticmethod
    def export_data_bundle():
        """Exporta todos os dados do assistente em um dicionário serializável"""
        data = {
            "exported_at": timezone.now().isoformat(),
            "events": [
                {
                    "title": e.title,
                    "description": e.description,
                    "start_time": e.start_time.isoformat(),
                    "end_time": e.end_time.isoformat() if e.end_time else None,
                    "location": e.location,
                    "category": e.category,
                    "is_important": e.is_important,
                }
                for e in CalendarEvent.objects.all()
            ],
            "tasks": [
                {
                    "title": t.title,
                    "is_done": t.is_done,
                    "priority": t.priority,
                    "category": t.category,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "notes": t.notes,
                }
                for t in QuickTask.objects.all()
            ],
            "emails": [
                {
                    "sender": em.sender,
                    "subject": em.subject,
                    "snippet": em.snippet,
                    "is_important": em.is_important,
                    "received_at": em.received_at.isoformat() if em.received_at else None,
                }
                for em in EmailHighlight.objects.all()
            ],
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "action_type": m.action_type,
                    "action_details": m.action_details,
                    "created_at": m.created_at.isoformat(),
                }
                for m in ChatMessage.objects.all()
            ],
            "voice_memos": [
                {
                    "transcript": vm.transcript,
                    "intent_detected": vm.intent_detected,
                    "action_taken": vm.action_taken,
                    "created_at": vm.created_at.isoformat(),
                }
                for vm in VoiceMemo.objects.all()
            ],
        }
        return data

    @staticmethod
    def import_data_bundle(data):
        """Importa registros a partir de um dicionário exportado, evitando duplicatas"""
        imported_counts = {"events": 0, "tasks": 0, "emails": 0, "messages": 0}

        # 1. Tarefas
        for item in data.get("tasks", []):
            if not QuickTask.objects.filter(title=item["title"]).exists():
                QuickTask.objects.create(
                    title=item["title"],
                    is_done=item.get("is_done", False),
                    priority=item.get("priority", "medium"),
                    category=item.get("category", "work"),
                    notes=item.get("notes", "")
                )
                imported_counts["tasks"] += 1

        # 2. Compromissos
        for item in data.get("events", []):
            if not CalendarEvent.objects.filter(title=item["title"], start_time=item["start_time"]).exists():
                CalendarEvent.objects.create(
                    title=item["title"],
                    description=item.get("description", ""),
                    start_time=item["start_time"],
                    end_time=item.get("end_time"),
                    location=item.get("location", ""),
                    category=item.get("category", "work"),
                    is_important=item.get("is_important", False)
                )
                imported_counts["events"] += 1

        # 3. E-mails
        for item in data.get("emails", []):
            if not EmailHighlight.objects.filter(sender=item["sender"], subject=item["subject"]).exists():
                EmailHighlight.objects.create(
                    sender=item["sender"],
                    subject=item["subject"],
                    snippet=item.get("snippet", ""),
                    is_important=item.get("is_important", True),
                    received_at=item.get("received_at") or timezone.now()
                )
                imported_counts["emails"] += 1

        # 4. Memorandos de Voz
        for item in data.get("voice_memos", []):
            if not VoiceMemo.objects.filter(transcript=item.get("transcript", "")).exists():
                VoiceMemo.objects.create(
                    transcript=item.get("transcript", ""),
                    intent_detected=item.get("intent_detected", "note"),
                    action_taken=item.get("action_taken", ""),
                    is_processed=True
                )
                imported_counts["memos"] = imported_counts.get("memos", 0) + 1

        return imported_counts

    @staticmethod
    def save_cloud_url_to_env(db_url):
        """Salva a nova DATABASE_URL no arquivo .env local com segurança"""
        env_path = os.path.join(settings.BASE_DIR, '.env')
        url_str = db_url.strip()

        lines = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.strip().startswith('DATABASE_URL='):
                new_lines.append(f'DATABASE_URL={url_str}\n')
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f'\nDATABASE_URL={url_str}\n')

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True

    @staticmethod
    def sync_client_data(client_items=None, last_sync_iso=None):
        """Sincronização bidirecional em tempo real entre dispositivos (celular <-> computador <-> Supabase)"""
        now = timezone.now()
        client_items = client_items or {}
        imported_counts = {"tasks": 0, "events": 0}

        # 1. Aplica tarefas criadas offline no cliente
        for t in client_items.get("tasks", []):
            title = t.get("title", "").strip()
            if title and not QuickTask.objects.filter(title=title, due_date=now.date()).exists():
                QuickTask.objects.create(
                    title=title,
                    priority=t.get("priority", "medium"),
                    category=t.get("category", "work"),
                    is_done=bool(t.get("is_done", False)),
                    due_date=now.date()
                )
                imported_counts["tasks"] += 1

        # 2. Aplica eventos criados offline no cliente
        for ev in client_items.get("events", []):
            title = ev.get("title", "").strip()
            start_str = ev.get("start_time")
            if title and start_str:
                try:
                    s_dt = timezone.datetime.fromisoformat(start_str)
                    if timezone.is_naive(s_dt):
                        s_dt = timezone.make_aware(s_dt)
                    if not CalendarEvent.objects.filter(title=title, start_time=s_dt).exists():
                        CalendarEvent.objects.create(
                            title=title,
                            start_time=s_dt,
                            category=ev.get("category", "work"),
                            is_important=bool(ev.get("is_important", False))
                        )
                        imported_counts["events"] += 1
                except Exception as e:
                    print(f"Erro ao sincronizar evento offline: {e}")

        # 3. Retorna o estado atualizado da nuvem para o cliente
        events_qs = CalendarEvent.objects.all().order_by('start_time')
        tasks_qs = QuickTask.objects.filter(due_date=now.date()).order_by('is_done', '-priority')

        cloud_status = CloudDatabaseService.get_status()

        return {
            "success": True,
            "server_time": now.isoformat(),
            "is_cloud": cloud_status["is_cloud"],
            "provider": cloud_status["provider"],
            "imported_counts": imported_counts,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "is_done": t.is_done,
                    "priority": t.priority,
                    "category": t.category,
                    "category_label": t.get_category_display(),
                }
                for t in tasks_qs
            ],
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "start_time": timezone.localtime(e.start_time).strftime("%H:%M"),
                    "start_time_iso": e.start_time.isoformat(),
                    "category": e.category,
                    "is_important": e.is_important,
                }
                for e in events_qs
            ]
        }


class BackupService:
    """Serviço de Backup Automático Periódico (JSON no Servidor + Envio de Arquivo via Telegram)"""

    @staticmethod
    def get_backups_dir():
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @staticmethod
    def create_backup_file():
        """Exporta bundle completo de dados e salva em arquivo JSON datado na pasta backups/"""
        backup_dir = BackupService.get_backups_dir()
        now = timezone.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"backup_assistente_{timestamp}.json"
        filepath = os.path.join(backup_dir, filename)

        data = CloudDatabaseService.export_data_bundle()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        file_size_kb = round(os.path.getsize(filepath) / 1024, 2)

        # Remove backups muito antigos mantendo os 10 mais recentes
        try:
            existing = sorted([
                os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith('backup_') and f.endswith('.json')
            ], key=os.path.getmtime)
            while len(existing) > 10:
                oldest = existing.pop(0)
                os.remove(oldest)
        except Exception as e:
            print(f"Erro ao limpar backups antigos: {e}")

        # Atualiza timestamp em UserPreference
        pref = UserPreference.objects.first()
        if pref:
            pref.last_backup_at = now
            pref.save()

        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "size_kb": file_size_kb,
            "timestamp": timezone.localtime(now).strftime("%d/%m/%Y às %H:%M:%S"),
            "events_count": len(data.get("events", [])),
            "tasks_count": len(data.get("tasks", [])),
            "emails_count": len(data.get("emails", [])),
            "messages_count": len(data.get("messages", [])),
            "memos_count": len(data.get("voice_memos", [])),
        }

    @staticmethod
    def send_backup_to_telegram(custom_caption=None):
        """Cria o backup em JSON e envia o arquivo real diretamente como documento anexado no Telegram"""
        import requests
        pref = UserPreference.objects.first()
        bot_token = (pref.telegram_bot_token if pref and pref.telegram_bot_token else None) or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = (pref.telegram_chat_id if pref and pref.telegram_chat_id else None) or os.getenv("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            return {"success": False, "error": "Token do Telegram ou Chat ID não configurados nas preferências."}

        backup_info = BackupService.create_backup_file()
        filepath = backup_info["filepath"]
        filename = backup_info["filename"]

        caption = custom_caption or (
            f"📦 *BACKUP AUTOMÁTICO - BELLA ASSISTENTE*\n\n"
            f"📅 *Data:* {backup_info['timestamp']}\n"
            f"💾 *Tamanho:* {backup_info['size_kb']} KB\n"
            f"📊 *Conteúdo salvo:*\n"
            f"  * 📅 Compromissos: {backup_info['events_count']}\n"
            f"  * 🎯 Tarefas: {backup_info['tasks_count']}\n"
            f"  * ✉️ E-mails: {backup_info['emails_count']}\n"
            f"  * 💬 Mensagens: {backup_info['messages_count']}\n"
            f"  * 🎙️ Memorandos de Voz: {backup_info['memos_count']}\n\n"
            f"_Seu backup semanal está seguro e pode ser restaurado a qualquer momento._"
        )

        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendDocument"

        try:
            with open(filepath, 'rb') as doc_file:
                files = {'document': (filename, doc_file, 'application/json')}
                data = {
                    'chat_id': chat_id.strip(),
                    'caption': caption,
                    'parse_mode': 'Markdown'
                }
                res = requests.post(url, data=data, files=files, timeout=25)
                res_json = res.json()

                if res_json.get("ok"):
                    return {
                        "success": True,
                        "backup_info": backup_info,
                        "telegram_message_id": res_json.get("result", {}).get("message_id"),
                        "message": "Backup gerado e enviado ao seu Telegram com sucesso!"
                    }
                else:
                    return {
                        "success": False,
                        "backup_info": backup_info,
                        "error": res_json.get("description", "Falha no envio para o Telegram")
                    }
        except Exception as e:
            return {"success": False, "backup_info": backup_info, "error": str(e)}

    @staticmethod
    def check_and_run_weekly_backup():
        """Verifica se é hora de rodar o backup semanal automático (chamado periodicamente pela aplicação)"""
        pref = UserPreference.objects.first()
        if not pref or not pref.auto_backup_enabled:
            return {"ran": False, "reason": "Backup automático desativado"}

        now = timezone.now()
        should_run = False

        if not pref.last_backup_at:
            should_run = True
        else:
            diff_days = (now - pref.last_backup_at).total_seconds() / 86400
            if diff_days >= 7.0:
                should_run = True

        if should_run:
            if pref.auto_backup_telegram and pref.telegram_bot_token and pref.telegram_chat_id:
                result = BackupService.send_backup_to_telegram()
            else:
                info = BackupService.create_backup_file()
                result = {"success": True, "backup_info": info, "message": "Backup local gerado com sucesso."}
            return {"ran": True, "result": result}

        return {"ran": False, "reason": "Backup recente em dia (menos de 7 dias)"}

