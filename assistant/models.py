from django.db import models
from django.utils import timezone

class Theme(models.Model):
    """Modelo para gerenciamento visual e personalização de temas no Django"""
    name = models.CharField(max_length=60, unique=True, verbose_name="Nome do Tema")
    slug = models.SlugField(max_length=60, unique=True)
    description = models.TextField(blank=True, verbose_name="Descrição")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    is_default = models.BooleanField(default=False, verbose_name="Tema Padrão")
    
    # Variáveis de Cores e Estilo CSS
    primary_color = models.CharField(max_length=25, default="#6366f1", verbose_name="Cor Primária")
    secondary_color = models.CharField(max_length=25, default="#8b5cf6", verbose_name="Cor Secundária")
    accent_color = models.CharField(max_length=25, default="#10b981", verbose_name="Cor de Destaque")
    bg_gradient_start = models.CharField(max_length=25, default="#0f172a", verbose_name="Início Gradiente Fundo")
    bg_gradient_end = models.CharField(max_length=25, default="#1e1b4b", verbose_name="Fim Gradiente Fundo")
    card_bg = models.CharField(max_length=40, default="rgba(30, 41, 59, 0.75)", verbose_name="Fundo do Card (RGBA)")
    card_border = models.CharField(max_length=40, default="rgba(255, 255, 255, 0.12)", verbose_name="Borda do Card")
    text_color = models.CharField(max_length=25, default="#f8fafc", verbose_name="Cor de Texto")
    text_muted = models.CharField(max_length=25, default="#94a3b8", verbose_name="Cor de Texto Secundário")
    font_family = models.CharField(max_length=100, default="'Inter', sans-serif", verbose_name="Fonte")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tema Visual"
        verbose_name_plural = "Temas Visuais"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} {'(Padrão)' if self.is_default else ''}"


class UserPreference(models.Model):
    """Preferências do Usuário, Localização e Chaves de Integração"""
    city_name = models.CharField(max_length=100, default="Itobi, SP", verbose_name="Cidade Padrão")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, default=-21.7336, verbose_name="Latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, default=-46.9744, verbose_name="Longitude")
    gemini_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Gemini API Key (Opcional)")
    active_theme = models.ForeignKey(Theme, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    enable_voice = models.BooleanField(default=True, verbose_name="Leitura de Voz Ativada")
    daily_briefing_time = models.TimeField(default="08:00", verbose_name="Horário do Resumo")
    telegram_bot_token = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token Bot Telegram")
    telegram_chat_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Chat ID Telegram")
    whatsapp_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="Número WhatsApp (ex: 5519999999999)")
    auto_send_telegram = models.BooleanField(default=False, verbose_name="Envio Automático no Telegram")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferência do Sistema"
        verbose_name_plural = "Preferências do Sistema"

    def __str__(self):
        return f"Configurações ({self.city_name})"


class CalendarEvent(models.Model):
    """Compromissos agendados em ordem cronológica"""
    CATEGORY_CHOICES = [
        ('work', 'Trabalho / Reunião'),
        ('personal', 'Pessoal'),
        ('health', 'Saúde / Bem-estar'),
        ('study', 'Estudos / Projetos'),
        ('other', 'Outros'),
    ]
    title = models.CharField(max_length=200, verbose_name="Título do Compromisso")
    description = models.TextField(blank=True, verbose_name="Descrição / Pauta")
    start_time = models.DateTimeField(verbose_name="Data e Hora de Início")
    end_time = models.DateTimeField(verbose_name="Data e Hora de Fim", blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, verbose_name="Local / Link")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='work', verbose_name="Categoria")
    is_important = models.BooleanField(default=False, verbose_name="Prioridade Alta")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compromisso de Agenda"
        verbose_name_plural = "Agenda de Compromissos"
        ordering = ['start_time']

    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.title}"


class EmailHighlight(models.Model):
    """Mensagens e destaques importantes da caixa de entrada"""
    sender = models.CharField(max_length=150, verbose_name="Remetente")
    sender_email = models.EmailField(blank=True, verbose_name="E-mail do Remetente")
    subject = models.CharField(max_length=250, verbose_name="Assunto")
    snippet = models.TextField(verbose_name="Trecho / Resumo")
    received_at = models.DateTimeField(default=timezone.now, verbose_name="Recebido em")
    is_important = models.BooleanField(default=True, verbose_name="Importante / Destaque")
    is_read = models.BooleanField(default=False, verbose_name="Lido")
    action_required = models.BooleanField(default=False, verbose_name="Exige Ação")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Destaque de E-mail"
        verbose_name_plural = "Destaques de E-mails"
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.sender}: {self.subject}"


class DailyBriefing(models.Model):
    """Histórico de Resumos do Dia gerados pela IA Gemini"""
    date = models.DateField(default=timezone.now, verbose_name="Data de Referência")
    weather_city = models.CharField(max_length=100, default="Itobi, SP", verbose_name="Cidade")
    weather_temp_min = models.FloatField(null=True, blank=True, verbose_name="Temp Mínima (°C)")
    weather_temp_max = models.FloatField(null=True, blank=True, verbose_name="Temp Máxima (°C)")
    weather_condition = models.CharField(max_length=150, blank=True, verbose_name="Condição Climática")
    usd_bid = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, verbose_name="Dólar Compra")
    usd_ask = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, verbose_name="Dólar Venda")
    usd_variation = models.CharField(max_length=30, blank=True, verbose_name="Variação Dólar")
    gemini_summary = models.TextField(verbose_name="Resumo Gerado pelo Gemini")
    agenda_count = models.IntegerField(default=0, verbose_name="Total de Compromissos")
    email_count = models.IntegerField(default=0, verbose_name="Total de E-mails Destaque")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resumo Diário"
        verbose_name_plural = "Resumos Diários"
        ordering = ['-created_at']

    def __str__(self):
        return f"Briefing de {self.date.strftime('%d/%m/%Y')} às {self.created_at.strftime('%H:%M')}"


class ChatMessage(models.Model):
    """Mensagens trocadas no chat interativo com o assistente Gemini"""
    ROLE_CHOICES = [
        ('user', 'Usuário'),
        ('assistant', 'Assistente Gemini'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    content = models.TextField(verbose_name="Conteúdo da Mensagem")
    action_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ação Executada")
    action_details = models.TextField(blank=True, null=True, verbose_name="Detalhes da Ação (JSON)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensagem do Chat"
        verbose_name_plural = "Mensagens do Chat"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:40]}"


class QuickTask(models.Model):
    """Tarefas rápidas do widget de produtividade diária"""
    PRIORITY_CHOICES = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
    ]
    CATEGORY_CHOICES = [
        ('work', '💼 Trabalho'),
        ('personal', '🏠 Pessoal'),
        ('health', '💪 Saúde'),
        ('study', '📚 Estudos'),
        ('other', '📌 Outros'),
    ]
    title = models.CharField(max_length=200, verbose_name="Tarefa")
    is_done = models.BooleanField(default=False, verbose_name="Concluída")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="Prioridade")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='work', verbose_name="Categoria")
    due_date = models.DateField(default=timezone.now, verbose_name="Data")
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Concluída em")

    class Meta:
        verbose_name = "Tarefa Rápida"
        verbose_name_plural = "Tarefas Rápidas"
        ordering = ['is_done', '-priority', 'created_at']

    def __str__(self):
        status = "✅" if self.is_done else "⬜"
        return f"{status} {self.title}"

