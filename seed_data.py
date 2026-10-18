import os
import django
from datetime import datetime, time
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from assistant.models import Theme, UserPreference, CalendarEvent, EmailHighlight
from assistant.services import BriefingOrchestrator

def seed():
    print("Iniciando população de temas e dados iniciais...")
    
    # 1. Cria Superusuário para o Django Admin se não existir
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@agente01.local", "admin123")
        print("[OK] Superusuario 'admin' criado com sucesso (senha: admin123).")

    # 2. Popula os Temas do Django
    themes_data = [
        {
            "name": "Midnight Indigo",
            "slug": "midnight-indigo",
            "description": "Gradiente profundo azul-noite com acentos em índigo e esmeralda.",
            "is_default": True,
            "primary_color": "#6366f1",
            "secondary_color": "#8b5cf6",
            "accent_color": "#10b981",
            "bg_gradient_start": "#0f172a",
            "bg_gradient_end": "#1e1b4b",
            "card_bg": "rgba(30, 41, 59, 0.75)",
            "card_border": "rgba(255, 255, 255, 0.12)",
            "text_color": "#f8fafc",
            "text_muted": "#94a3b8",
            "font_family": "'Inter', sans-serif"
        },
        {
            "name": "Cyberpunk Neon",
            "slug": "cyberpunk-neon",
            "description": "Fundo obsidiana com brilho neon ciano e magenta elétrico.",
            "is_default": False,
            "primary_color": "#06b6d4",
            "secondary_color": "#d946ef",
            "accent_color": "#22c55e",
            "bg_gradient_start": "#05050d",
            "bg_gradient_end": "#180b2b",
            "card_bg": "rgba(18, 12, 38, 0.8)",
            "card_border": "rgba(6, 182, 212, 0.25)",
            "text_color": "#fdf4ff",
            "text_muted": "#a5b4fc",
            "font_family": "'Outfit', sans-serif"
        },
        {
            "name": "Emerald Forest",
            "slug": "emerald-forest",
            "description": "Tons botânicos de ardósia escura com destaques em verde esmeralda e menta.",
            "is_default": False,
            "primary_color": "#10b981",
            "secondary_color": "#059669",
            "accent_color": "#34d399",
            "bg_gradient_start": "#06201b",
            "bg_gradient_end": "#022c22",
            "card_bg": "rgba(6, 45, 38, 0.75)",
            "card_border": "rgba(52, 211, 153, 0.18)",
            "text_color": "#ecfdf5",
            "text_muted": "#6ee7b7",
            "font_family": "'Inter', sans-serif"
        },
        {
            "name": "Sunset Horizon",
            "slug": "sunset-horizon",
            "description": "Gradiente crepuscular com notas de violeta, âmbar e coral solar.",
            "is_default": False,
            "primary_color": "#f59e0b",
            "secondary_color": "#f43f5e",
            "accent_color": "#fbbf24",
            "bg_gradient_start": "#1c1024",
            "bg_gradient_end": "#2d1222",
            "card_bg": "rgba(42, 21, 38, 0.78)",
            "card_border": "rgba(245, 158, 11, 0.2)",
            "text_color": "#fffbeb",
            "text_muted": "#fcd34d",
            "font_family": "'Outfit', sans-serif"
        },
        {
            "name": "Titanium Minimal",
            "slug": "titanium-minimal",
            "description": "Design industrial minimalista com contrastes nítidos e cinza grafite.",
            "is_default": False,
            "primary_color": "#38bdf8",
            "secondary_color": "#64748b",
            "accent_color": "#38bdf8",
            "bg_gradient_start": "#090d16",
            "bg_gradient_end": "#111827",
            "card_bg": "rgba(17, 24, 39, 0.85)",
            "card_border": "rgba(148, 163, 184, 0.15)",
            "text_color": "#ffffff",
            "text_muted": "#94a3b8",
            "font_family": "'Inter', sans-serif"
        }
    ]

    default_theme = None
    for td in themes_data:
        t, created = Theme.objects.update_or_create(slug=td["slug"], defaults=td)
        if t.is_default:
            default_theme = t
    print("[OK] 5 Temas premium cadastrados no Django com sucesso.")

    # 3. Preferência de Usuário
    pref, _ = UserPreference.objects.get_or_create(
        id=1,
        defaults={
            "city_name": "Itobi, SP",
            "latitude": -21.7336,
            "longitude": -46.9744,
            "active_theme": default_theme,
            "enable_voice": True,
            "daily_briefing_time": "08:00"
        }
    )
    if not pref.active_theme:
        pref.active_theme = default_theme
        pref.save()
    print("[OK] Preferencias do usuario configuradas para Itobi, SP.")

    # 4. Compromissos de Demonstração para Hoje
    now = timezone.now()
    today_start = now.date()
    
    events_data = [
        {
            "title": "Alinhamento Matinal & Prioridades da Semana",
            "description": "Revisão dos principais objetivos, métricas e pendências da equipe.",
            "start_time": timezone.make_aware(datetime.combine(today_start, time(9, 0))),
            "category": "work",
            "location": "Google Meet",
            "is_important": True
        },
        {
            "title": "Análise do Mercado e Fechamento do Dólar",
            "description": "Acompanhamento da cotação comercial USD/BRL e relatórios de câmbio.",
            "start_time": timezone.make_aware(datetime.combine(today_start, time(14, 30))),
            "category": "work",
            "location": "Sala Virtual de Análise",
            "is_important": False
        },
        {
            "title": "Caminhada / Treino ao Ar Livre em Itobi",
            "description": "Atividade física e pausa ativa no fim da tarde.",
            "start_time": timezone.make_aware(datetime.combine(today_start, time(18, 0))),
            "category": "health",
            "location": "Parque Municipal de Itobi",
            "is_important": False
        }
    ]

    for ed in events_data:
        if not CalendarEvent.objects.filter(title=ed["title"], start_time__date=today_start).exists():
            CalendarEvent.objects.create(**ed)
    print("[OK] Compromissos de agenda criados em ordem cronologica.")

    # 5. Destaques de E-mails
    emails_data = [
        {
            "sender": "Diretoria Financeira",
            "sender_email": "financeiro@empresa.com",
            "subject": "Aprovação do Orçamento Trimestral",
            "snippet": "Prezado, precisamos da sua validação final sobre as projeções cambiais para liberação do orçamento.",
            "is_important": True,
            "action_required": True
        },
        {
            "sender": "Equipe de Cloud & Infra",
            "sender_email": "cloud@empresa.com",
            "subject": "Sincronização do Banco de Dados Concluída",
            "snippet": "Os backups automáticos e replicação na nuvem foram finalizados sem inconformidades.",
            "is_important": False,
            "action_required": False
        },
        {
            "sender": "Notificações do Sistema",
            "sender_email": "alertas@agente01.local",
            "subject": "Resumo matinal disponível para leitura ou áudio",
            "snippet": "Seu briefing executivo foi gerado com sucesso. Clique para ouvir o resumo de voz no smartphone.",
            "is_important": True,
            "action_required": False
        }
    ]

    for em in emails_data:
        if not EmailHighlight.objects.filter(subject=em["subject"]).exists():
            EmailHighlight.objects.create(**em)
    print("[OK] Destaques de e-mails prioritarios cadastrados.")

    # 6. Gera o primeiro briefing completo
    print("[OK] Gerando primeiro briefing executivo do dia com dados reais...")
    BriefingOrchestrator.get_today_briefing(force_refresh=True)
    print("[OK] Sistema 100% pronto!")

if __name__ == '__main__':
    seed()
