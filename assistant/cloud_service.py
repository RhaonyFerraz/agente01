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
from .models import CalendarEvent, QuickTask, EmailHighlight, DailyBriefing, ChatMessage, UserPreference, Theme


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
