/**
 * Assistente Pessoal PWA - Aplicação Principal
 * Integração: Django REST API, Google Gemini, Open-Meteo, AwesomeAPI, Web Speech API
 */

class PersonalAssistantApp {
  constructor() {
    window.app = this;
    this.currentBriefing = null;
    this.activeTab = 'briefing';
    this.deferredPrompt = null;
    this.isSpeaking = false;
    this.speechUtterance = null;
    this.voiceReplyActive = true;
    this.recognition = null;
    this.isListening = false;
    this.continuousVoiceActive = false;
    this.continuousVoicePaused = false;
    this.continuousRecognition = null;
    this.isAssistantSpeakingLive = false;
    this.bellaVoice = null;
    this.bellaPitch = parseFloat(localStorage.getItem('bella_voice_pitch') || '1.18');
    this.bellaRate = parseFloat(localStorage.getItem('bella_voice_rate') || '1.06');
    this.selectedVoiceName = localStorage.getItem('bella_voice_name') || '';
    
    try {
      this.init();
    } catch (e) {
      console.error('Erro na inicialização do app:', e);
    }
  }

  init() {
    this.setupServiceWorker();
    this.setupInstallPrompt();
    this.setupDateDisplay();
    this.setupEventListeners();
    this.setupSpeechRecognition();
    this.setupContinuousVoice();
    this.setupTasksQuickAdd();
    this.setupAutoRefresh();
    this.setupBellaVoice();
    this.loadTodayBriefing();
    this.loadThemes();
    this.loadSettings();
    this.loadChatMessages();
    this.loadMultiCurrency();
    this.loadWeeklyForecast();
    this.loadTasks();
    this.loadCloudDbStatus();
    // Solicita perm. notif. com pequeno delay (não bloqueia)
    setTimeout(() => this.requestPushPermission(), 3000);
  }

  /* =========================================================================
     PWA SERVICE WORKER & INSTALAÇÃO
  ========================================================================= */
  setupServiceWorker() {
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
          .then((reg) => console.log('PWA ServiceWorker registrado com sucesso:', reg.scope))
          .catch((err) => console.warn('Erro ao registrar ServiceWorker:', err));
      });
    }

    // Monitora status online/offline
    const updateOnlineStatus = () => {
      const statusEl = document.getElementById('header-status');
      if (statusEl) {
        statusEl.textContent = navigator.onLine ? 'Online' : 'Offline (Cache)';
        statusEl.style.color = navigator.onLine ? 'var(--accent)' : '#f87171';
      }
    };
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();
  }

  setupInstallPrompt() {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;
      const banner = document.getElementById('pwa-install-banner');
      if (banner) banner.classList.remove('hidden');
    });

    const installBtn = document.getElementById('btn-install-pwa');
    if (installBtn) {
      installBtn.addEventListener('click', async () => {
        if (!this.deferredPrompt) return;
        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;
        console.log('Resultado da instalação PWA:', outcome);
        this.deferredPrompt = null;
        document.getElementById('pwa-install-banner').classList.add('hidden');
      });
    }
  }

  /* =========================================================================
     DATA E EVENTOS DA INTERFACE
  ========================================================================= */
  setupDateDisplay() {
    const dateEl = document.getElementById('current-date-badge');
    if (!dateEl) return;
    
    const now = new Date();
    const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
    const dateStr = now.toLocaleDateString('pt-BR', options);
    // Capitaliza primeira letra
    dateEl.textContent = dateStr.charAt(0).toUpperCase() + dateStr.slice(1);
  }

  setupEventListeners() {
    // Abas de navegação
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        this.switchTab(tab);
      });
    });

    // Botão de Atualizar
    const refreshBtn = document.getElementById('btn-refresh-briefing');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.forceRefreshBriefing());
    }

    // Botões de Voz (TTS)
    const voiceBtn = document.getElementById('btn-voice-read');
    if (voiceBtn) voiceBtn.addEventListener('click', () => this.toggleSpeech());

    const listenCardBtn = document.getElementById('btn-listen-card');
    if (listenCardBtn) listenCardBtn.addEventListener('click', () => this.toggleSpeech());

    // Conversor Rápido USD -> BRL
    const convInput = document.getElementById('quick-usd-input');
    if (convInput) {
      convInput.addEventListener('input', () => this.updateConverter());
    }

    // Abertura de Modais
    const addEventBtn = document.getElementById('btn-add-event');
    if (addEventBtn) addEventBtn.addEventListener('click', () => this.openModal('modal-event'));

    const addEmailBtn = document.getElementById('btn-add-email');
    if (addEmailBtn) addEmailBtn.addEventListener('click', () => this.openModal('modal-email'));

    // Submissão de Formulários
    const eventForm = document.getElementById('form-new-event');
    if (eventForm) eventForm.addEventListener('submit', (e) => this.handleNewEvent(e));

    const emailForm = document.getElementById('form-new-email');
    if (emailForm) emailForm.addEventListener('submit', (e) => this.handleNewEmail(e));

    // Salvar Chave Gemini
    const saveKeyBtn = document.getElementById('btn-save-key');
    if (saveKeyBtn) saveKeyBtn.addEventListener('click', () => this.saveGeminiKey());

    // Atualizar Cidade
    const saveCityBtn = document.getElementById('btn-save-city');
    if (saveCityBtn) saveCityBtn.addEventListener('click', () => this.saveCity());

    // Eventos do Chat Interativo
    const chatSendBtn = document.getElementById('btn-chat-send');
    if (chatSendBtn) chatSendBtn.addEventListener('click', () => this.handleChatSend());

    const chatInput = document.getElementById('chat-text-input');
    if (chatInput) {
      chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.handleChatSend();
        }
      });
    }

    const micBtn = document.getElementById('btn-mic-input');
    if (micBtn) micBtn.addEventListener('click', () => this.toggleVoiceInput());

    const toggleVoiceReplyBtn = document.getElementById('btn-toggle-voice-reply');
    if (toggleVoiceReplyBtn) toggleVoiceReplyBtn.addEventListener('click', () => this.toggleVoiceReply());

    // Eventos de Notificações WhatsApp & Telegram
    const shareWaBtn = document.getElementById('btn-share-whatsapp');
    if (shareWaBtn) shareWaBtn.addEventListener('click', () => this.shareOnWhatsApp());

    const sendTgBtn = document.getElementById('btn-send-telegram');
    if (sendTgBtn) sendTgBtn.addEventListener('click', () => this.sendToTelegram());

    const testTgBtn = document.getElementById('btn-test-telegram');
    if (testTgBtn) testTgBtn.addEventListener('click', () => this.testTelegramConnection());

    const saveNotifBtn = document.getElementById('btn-save-notifications');
    if (saveNotifBtn) saveNotifBtn.addEventListener('click', () => this.saveNotificationPreferences());
  }

  switchTab(tabName) {
    this.activeTab = tabName;
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const targetPane = document.getElementById(`tab-${tabName}`);
    if (targetPane) targetPane.classList.add('active');

    const targetNav = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (targetNav) targetNav.classList.add('active');

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* =========================================================================
     CARREGAMENTO DO BRIEFING (API DJANGO + GEMINI)
  ========================================================================= */
  async loadTodayBriefing() {
    this.showBriefingLoading(true);
    try {
      const res = await fetch('/api/briefing/today/');
      if (!res.ok) throw new Error('Falha ao obter o briefing');
      const data = await res.json();
      this.currentBriefing = data;
      this.renderBriefing(data);
    } catch (err) {
      console.error('Erro ao carregar briefing:', err);
      this.showToast('Erro ao carregar dados do dia. Tentando novamente...');
    } finally {
      this.showBriefingLoading(false);
    }
  }

  async forceRefreshBriefing() {
    const icon = document.querySelector('.spin-target');
    if (icon) icon.classList.add('spin-active');
    this.showToast('Consultando clima, cotações e gerando síntese com IA...');

    try {
      const res = await fetch('/api/briefing/generate/', { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        this.currentBriefing = json.data;
        this.renderBriefing(json.data);
        this.showToast('Resumo atualizado com sucesso!');
      }
    } catch (err) {
      console.error(err);
      this.showToast('Não foi possível regenerar o briefing.');
    } finally {
      if (icon) icon.classList.remove('spin-active');
    }
  }

  renderBriefing(data) {
    // 1. Resumo Executivo Gemini
    const summaryEl = document.getElementById('gemini-briefing-content');
    if (summaryEl && data.summary) {
      // Converte markdown básico (negrito e bullet points) para HTML limpo
      summaryEl.innerHTML = this.formatMarkdown(data.summary);
    }

    // 2. Clima (Itobi, SP)
    if (data.weather) {
      const w = data.weather;
      const safeSetText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
      };

      safeSetText('weather-city-badge', w.city || 'Itobi, SP');
      safeSetText('weather-icon-badge', w.icon || '⛅');
      safeSetText('weather-current-temp', Math.round(w.current_temp));
      safeSetText('weather-temp-max', `${Math.round(w.temp_max)}°`);
      safeSetText('weather-temp-min', `${Math.round(w.temp_min)}°`);
      safeSetText('weather-condition-desc', w.condition);
      safeSetText('weather-rain-prob', `${w.rain_prob}%`);
      safeSetText('weather-humidity', `${w.humidity}%`);
      safeSetText('weather-wind', `${w.wind_speed} km/h`);
    }

    // 3. Cotação do Dólar (USD/BRL)
    if (data.currency) {
      const c = data.currency;
      const safeSetText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
      };

      safeSetText('currency-bid-val', c.bid.toFixed(2).replace('.', ','));
      safeSetText('currency-ask-val', c.ask.toFixed(2).replace('.', ','));
      safeSetText('currency-high-val', `R$ ${c.high.toFixed(2).replace('.', ',')}`);
      safeSetText('currency-low-val', `R$ ${c.low.toFixed(2).replace('.', ',')}`);
      
      const varEl = document.getElementById('currency-variation-badge');
      if (varEl) {
        varEl.textContent = c.variation;
        if (c.variation && c.variation.includes('-')) {
          varEl.classList.add('negative');
        } else {
          varEl.classList.remove('negative');
        }
      }

      this._usdBid = c.bid;
      this.updateConverter();
    }

    // 4. Agenda Rápida & Timeline Completa
    this.renderAgenda(data.events || []);

    // 5. E-mails Rápidos & Lista Completa
    this.renderEmails(data.emails || []);

    // 6. Atualiza tema dinâmico se retornado
    if (data.theme) {
      this.applyThemeVars(data.theme);
    }
  }

  formatMarkdown(text) {
    if (!text) return '';
    // Substitui negrito **texto** por <strong>texto</strong>
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Transforma * ou • em marcadores visuais destacados
    formatted = formatted.replace(/^\s*[\*•]\s+/gm, '<span class="bullet-dot">•</span> ');
    return formatted;
  }

  showBriefingLoading(isLoading) {
    const skeleton = document.getElementById('briefing-loading-skeleton');
    const content = document.getElementById('gemini-briefing-content');
    if (!skeleton || !content) return;

    if (isLoading) {
      skeleton.classList.remove('hidden');
      content.classList.add('hidden');
    } else {
      skeleton.classList.add('hidden');
      content.classList.remove('hidden');
    }
  }

  /* =========================================================================
     AGENDA E EMAILS
  ========================================================================= */
  renderAgenda(events) {
    const quickList = document.getElementById('quick-agenda-list');
    const fullTimeline = document.getElementById('agenda-full-timeline');

    if (!events || events.length === 0) {
      const emptyHtml = '<p class="empty-state-msg">Nenhum compromisso agendado para hoje. Dia livre!</p>';
      if (quickList) quickList.innerHTML = emptyHtml;
      if (fullTimeline) fullTimeline.innerHTML = emptyHtml;
      return;
    }

    // Quick List (Top 3)
    if (quickList) {
      quickList.innerHTML = events.slice(0, 3).map(ev => `
        <div class="preview-item">
          <div class="preview-item-left">
            <span class="item-time">${ev.start_time}</span>
            <span>${ev.title}</span>
          </div>
          ${ev.is_important ? '<span class="item-badge-important">Prioritário</span>' : ''}
        </div>
      `).join('');
    }

    // Full Timeline
    if (fullTimeline) {
      fullTimeline.innerHTML = events.map(ev => `
        <div class="timeline-card ${ev.is_important ? 'important' : ''}">
          <div class="timeline-time-col">
            <strong>${ev.start_time}</strong>
            <span class="category-tag">${ev.category_label || ev.category}</span>
          </div>
          <div class="timeline-content">
            <h4>${ev.title}</h4>
            ${ev.description ? `<p>${ev.description}</p>` : ''}
            ${ev.location ? `<p style="font-size:0.75rem; margin-top:4px;">📍 ${ev.location}</p>` : ''}
          </div>
        </div>
      `).join('');
    }
  }

  renderEmails(emails) {
    const quickList = document.getElementById('quick-email-list');
    const fullList = document.getElementById('emails-full-list');

    if (!emails || emails.length === 0) {
      const emptyHtml = '<p class="empty-state-msg">Caixa de entrada sem mensagens prioritárias.</p>';
      if (quickList) quickList.innerHTML = emptyHtml;
      if (fullList) fullList.innerHTML = emptyHtml;
      return;
    }

    // Quick List (Top 3)
    if (quickList) {
      quickList.innerHTML = emails.slice(0, 3).map(em => `
        <div class="preview-item">
          <div class="preview-item-left">
            <span>✉️</span>
            <div>
              <strong style="display:block; font-size:0.8rem;">${em.sender}</strong>
              <span style="font-size:0.75rem; color:var(--text-muted);">${em.subject}</span>
            </div>
          </div>
          ${em.is_important ? '<span class="item-badge-important">Atenção</span>' : ''}
        </div>
      `).join('');
    }

    // Full List
    if (fullList) {
      fullList.innerHTML = emails.map(em => `
        <div class="email-card ${em.is_important ? 'important' : ''}">
          <div class="email-header-row">
            <span class="email-sender">${em.sender}</span>
            <span class="email-time">${em.received_at}</span>
          </div>
          <div class="email-subject">${em.subject}</div>
          <div class="email-snippet">${em.snippet}</div>
        </div>
      `).join('');
    }
  }

  /* =========================================================================
     SÍNTESE DE VOZ (TEXT-TO-SPEECH)
  ========================================================================= */
  toggleSpeech() {
    if (!('speechSynthesis' in window)) {
      this.showToast('Síntese de voz não suportada pelo seu navegador.');
      return;
    }

    if (this.isSpeaking) {
      window.speechSynthesis.cancel();
      this.isSpeaking = false;
      this.updateVoiceIcon(false);
      this.showToast('Áudio pausado.');
      return;
    }

    const summaryText = this.currentBriefing?.summary;
    if (!summaryText) {
      this.showToast('Nenhum texto disponível para leitura.');
      return;
    }

    // Remove asteriscos e caracteres de markdown para pronúncia natural
    const cleanText = summaryText
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/#/g, '')
      .replace(/•/g, '')
      .replace(/\n+/g, '. ');

    this.speechUtterance = new SpeechSynthesisUtterance(cleanText);
    this.configureBellaUtterance(this.speechUtterance);

    this.speechUtterance.onstart = () => {
      this.isSpeaking = true;
      this.updateVoiceIcon(true);
      this.showToast('Reproduzindo resumo por voz...');
    };

    this.speechUtterance.onend = () => {
      this.isSpeaking = false;
      this.updateVoiceIcon(false);
    };

    this.speechUtterance.onerror = () => {
      this.isSpeaking = false;
      this.updateVoiceIcon(false);
    };

    window.speechSynthesis.speak(this.speechUtterance);
  }

  updateVoiceIcon(isPlaying) {
    const btn = document.getElementById('btn-voice-read');
    if (!btn) return;
    btn.style.background = isPlaying ? 'var(--accent)' : '';
  }

  /* =========================================================================
     TEMAS DINÂMICOS DO DJANGO
  ========================================================================= */
  async loadThemes() {
    try {
      const res = await fetch('/api/themes/');
      const data = await res.json();
      const container = document.getElementById('themes-grid-container');
      if (!container || !data.themes) return;

      container.innerHTML = data.themes.map(t => `
        <div class="theme-pill-card ${t.is_selected ? 'selected' : ''}" onclick="app.selectTheme(${t.id})">
          <div class="theme-preview-palette">
            <span class="palette-color" style="background:${t.primary_color}"></span>
            <span class="palette-color" style="background:${t.secondary_color}"></span>
            <span class="palette-color" style="background:${t.accent_color}"></span>
            <span class="palette-color" style="background:${t.bg_gradient_start}"></span>
          </div>
          <span class="theme-name">${t.name}</span>
        </div>
      `).join('');
    } catch (err) {
      console.warn('Erro ao carregar temas:', err);
    }
  }

  async selectTheme(themeId) {
    try {
      const res = await fetch('/api/themes/select/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme_id: themeId })
      });
      const data = await res.json();
      if (data.status === 'success') {
        this.showToast(`Tema "${data.active_theme}" aplicado!`);
        this.loadThemes();
        this.loadTodayBriefing();
      }
    } catch (err) {
      console.error(err);
      this.showToast('Erro ao trocar tema.');
    }
  }

  applyThemeVars(theme) {
    const root = document.documentElement;
    if (theme.primary_color) root.style.setProperty('--primary', theme.primary_color);
    if (theme.secondary_color) root.style.setProperty('--secondary', theme.secondary_color);
    if (theme.accent_color) root.style.setProperty('--accent', theme.accent_color);
    if (theme.bg_gradient_start) root.style.setProperty('--bg-start', theme.bg_gradient_start);
    if (theme.bg_gradient_end) root.style.setProperty('--bg-end', theme.bg_gradient_end);
    if (theme.card_bg) root.style.setProperty('--card-bg', theme.card_bg);
    if (theme.card_border) root.style.setProperty('--card-border', theme.card_border);
    if (theme.text_color) root.style.setProperty('--text', theme.text_color);
  }

  /* =========================================================================
     CONFIGURAÇÕES & MODAIS
  ========================================================================= */
  async loadSettings() {
    try {
      const res = await fetch('/api/settings/');
      const data = await res.json();
      if (data.city_name) {
        const cityInput = document.getElementById('cfg-city-name');
        if (cityInput) cityInput.value = data.city_name;
      }
      if (data.has_gemini_key) {
        const keyInput = document.getElementById('cfg-gemini-key');
        if (keyInput) keyInput.placeholder = 'Chave do Gemini configurada e ativa ✓';
      }
      if (data.telegram_bot_token) {
        const tgTokenInput = document.getElementById('cfg-tg-token');
        if (tgTokenInput) tgTokenInput.value = data.telegram_bot_token;
      }
      if (data.telegram_chat_id) {
        const tgChatInput = document.getElementById('cfg-tg-chat-id');
        if (tgChatInput) tgChatInput.value = data.telegram_chat_id;
      }
      if (data.whatsapp_number) {
        const waNumberInput = document.getElementById('cfg-wa-number');
        if (waNumberInput) waNumberInput.value = data.whatsapp_number;
      }
      const autoTgInput = document.getElementById('cfg-auto-tg');
      if (autoTgInput) autoTgInput.checked = !!data.auto_send_telegram;
    } catch (err) {
      console.warn(err);
    }
  }

  async shareOnWhatsApp() {
    this.showToast('Preparando resumo para o WhatsApp...');
    try {
      const res = await fetch('/api/notifications/whatsapp/text/');
      const data = await res.json();
      if (data.url) {
        window.open(data.url, '_blank');
      }
    } catch (err) {
      console.error(err);
      this.showToast('Erro ao abrir o WhatsApp.');
    }
  }

  async sendToTelegram() {
    this.showToast('Enviando resumo via bot do Telegram...');
    try {
      const res = await fetch('/api/notifications/telegram/send/', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        this.showToast('✈️ Resumo enviado com sucesso ao seu Telegram!');
      } else {
        this.showToast(`Telegram: ${data.error || 'Falha ao enviar'}`);
      }
    } catch (err) {
      console.error(err);
      this.showToast('Erro ao conectar com o serviço do Telegram.');
    }
  }

  async testTelegramConnection() {
    const token = document.getElementById('cfg-tg-token')?.value.trim();
    const chatId = document.getElementById('cfg-tg-chat-id')?.value.trim();

    if (!token || !chatId) {
      this.showToast('Informe o Token do Bot e o Chat ID para testar.');
      return;
    }

    this.showToast('Disparando mensagem de teste...');
    try {
      const res = await fetch('/api/notifications/telegram/test/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_token: token, chat_id: chatId })
      });
      const data = await res.json();
      if (data.success) {
        this.showToast('🔔 Conexão com o Telegram validada com sucesso!');
      } else {
        this.showToast(`Erro Telegram: ${data.error || 'Token ou ID inválidos'}`);
      }
    } catch (err) {
      console.error(err);
      this.showToast('Não foi possível testar o Telegram.');
    }
  }

  async saveNotificationPreferences() {
    const token = document.getElementById('cfg-tg-token')?.value.trim();
    const chatId = document.getElementById('cfg-tg-chat-id')?.value.trim();
    const waNumber = document.getElementById('cfg-wa-number')?.value.trim();
    const autoTg = document.getElementById('cfg-auto-tg')?.checked;

    try {
      const res = await fetch('/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          telegram_bot_token: token,
          telegram_chat_id: chatId,
          whatsapp_number: waNumber,
          auto_send_telegram: autoTg
        })
      });

      if (res.ok) {
        this.showToast('Configurações de notificação salvas com sucesso!');
      }
    } catch (err) {
      this.showToast('Erro ao salvar preferências.');
    }
  }

  async saveGeminiKey() {
    const input = document.getElementById('cfg-gemini-key');
    const key = input ? input.value.trim() : '';
    if (!key) {
      this.showToast('Por favor, informe a chave da API do Gemini.');
      return;
    }

    try {
      const res = await fetch('/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gemini_api_key: key })
      });
      if (res.ok) {
        this.showToast('Chave Gemini salva com sucesso!');
        input.value = '';
        input.placeholder = 'Chave do Gemini configurada e ativa ✓';
        this.forceRefreshBriefing();
      }
    } catch (err) {
      this.showToast('Erro ao salvar chave.');
    }
  }

  async saveCity() {
    const input = document.getElementById('cfg-city-name');
    const city = input ? input.value.trim() : '';
    if (!city) return;

    try {
      const res = await fetch('/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city_name: city })
      });
      if (res.ok) {
        this.showToast(`Cidade atualizada para "${city}"!`);
        this.forceRefreshBriefing();
      }
    } catch (err) {
      this.showToast('Erro ao atualizar cidade.');
    }
  }

  /* =========================================================================
     NUVEM DE DADOS: SUPABASE / POSTGRESQL / BACKUP
  ========================================================================= */
  async loadCloudDbStatus() {
    try {
      const res = await fetch('/api/cloud-db/status/');
      if (!res.ok) return;
      const data = await res.json();
      this.renderCloudDbStatus(data);
    } catch (err) {
      console.warn('Erro ao carregar status do banco de dados na nuvem:', err);
    }
  }

  renderCloudDbStatus(data) {
    const badge = document.getElementById('cloud-db-provider-badge');
    const dot = document.getElementById('cloud-db-status-dot');
    const statusText = document.getElementById('cloud-db-status-text');
    const latency = document.getElementById('cloud-db-latency');
    const records = document.getElementById('cloud-db-records-count');

    if (badge) {
      badge.textContent = data.provider || 'SQLite Local';
      badge.className = `cloud-badge ${data.is_cloud ? 'supabase' : 'sqlite'}`;
    }

    if (dot) {
      dot.className = `status-dot ${data.is_connected ? 'green' : 'red'}`;
    }

    if (statusText) {
      statusText.textContent = data.is_connected ? 'Conectado' : 'Desconectado';
    }

    if (latency && data.latency_ms !== null) {
      latency.textContent = `${data.latency_ms} ms`;
    }

    if (records) {
      records.textContent = `${data.total_records} registros`;
    }
  }

  toggleDbUrlVisibility() {
    const input = document.getElementById('cfg-cloud-db-url');
    const btn = document.getElementById('btn-toggle-db-url-visibility');
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      if (btn) btn.textContent = '🔒';
    } else {
      input.type = 'password';
      if (btn) btn.textContent = '👁️';
    }
  }

  async testCloudDbConnection() {
    const input = document.getElementById('cfg-cloud-db-url');
    const url = input ? input.value.trim() : '';

    if (!url) {
      this.showToast('Informe a URI do Supabase / PostgreSQL para testar.');
      return;
    }

    this.showToast('Testando conexão com a nuvem...');
    try {
      const res = await fetch('/api/cloud-db/test/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ database_url: url })
      });
      const data = await res.json();

      if (data.success) {
        this.showToast(`✅ ${data.message}`);
      } else {
        this.showToast(`❌ Falha: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      this.showToast('Erro ao testar conexão.');
    }
  }

  async saveCloudDbUrl() {
    const input = document.getElementById('cfg-cloud-db-url');
    const url = input ? input.value.trim() : '';

    if (!url) {
      this.showToast('Informe a URI do banco para conectar.');
      return;
    }

    this.showToast('Salvando credenciais e validando banco na nuvem...');
    try {
      const res = await fetch('/api/cloud-db/save/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ database_url: url })
      });
      const data = await res.json();

      if (data.success) {
        this.showToast('☁️ Banco de dados na nuvem configurado com sucesso!');
        await this.loadCloudDbStatus();
      } else {
        this.showToast(`Erro ao conectar: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      this.showToast('Erro ao salvar conexão com a nuvem.');
    }
  }

  exportCloudBackup() {
    this.showToast('Gerando backup de todos os seus dados...');
    window.location.href = '/api/cloud-db/export/';
  }

  async importCloudBackup(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    this.showToast('Lendo e restaurando arquivo de dados...');
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const json = JSON.parse(e.target.result);
          const res = await fetch('/api/cloud-db/import/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(json)
          });
          const result = await res.json();
          if (result.success) {
            const counts = result.imported;
            this.showToast(`✅ Dados restaurados: ${counts.events} eventos, ${counts.tasks} tarefas.`);
            await this.loadTodayBriefing();
            await this.loadTasks();
            await this.loadCloudDbStatus();
          } else {
            this.showToast(`Falha na importação: ${result.error}`);
          }
        } catch (parseErr) {
          this.showToast('Arquivo JSON inválido.');
        }
      };
      reader.readAsText(file);
    } catch (err) {
      console.error(err);
      this.showToast('Erro ao importar arquivo.');
    }
  }

  updateConverter() {
    const input = document.getElementById('quick-usd-input');
    const result = document.getElementById('quick-brl-result');
    if (!input || !result || !this.currentBriefing?.currency?.bid) return;

    const usdVal = parseFloat(input.value) || 0;
    const brlVal = usdVal * this.currentBriefing.currency.bid;
    result.textContent = brlVal.toFixed(2).replace('.', ',');
  }

  openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove('hidden');
  }

  closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add('hidden');
  }

  async handleNewEvent(e) {
    e.preventDefault();
    const title = document.getElementById('event-title').value;
    const time = document.getElementById('event-time').value;
    const category = document.getElementById('event-category').value;
    const location = document.getElementById('event-location').value;
    const important = document.getElementById('event-important').checked;

    const todayStr = new Date().toISOString().split('T')[0];
    const isoString = `${todayStr}T${time}:00`;

    try {
      const res = await fetch('/api/calendar/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          start_time: isoString,
          category,
          location,
          is_important: important
        })
      });

      if (res.ok) {
        this.showToast('Compromisso adicionado à agenda!');
        this.closeModal('modal-event');
        document.getElementById('form-new-event').reset();
        this.loadTodayBriefing();
      }
    } catch (err) {
      this.showToast('Erro ao salvar compromisso.');
    }
  }

  async handleNewEmail(e) {
    e.preventDefault();
    const sender = document.getElementById('email-sender').value;
    const subject = document.getElementById('email-subject').value;
    const snippet = document.getElementById('email-snippet').value;
    const important = document.getElementById('email-important').checked;

    try {
      const res = await fetch('/api/emails/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender,
          subject,
          snippet,
          is_important: important
        })
      });

      if (res.ok) {
        this.showToast('Destaque de e-mail adicionado!');
        this.closeModal('modal-email');
        document.getElementById('form-new-email').reset();
        this.loadTodayBriefing();
      }
    } catch (err) {
      this.showToast('Erro ao salvar e-mail.');
    }
  }

  showToast(message) {
    const toast = document.getElementById('toast-notification');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => {
      toast.classList.add('hidden');
    }, 3200);
  }

  /* =========================================================================
     CHAT INTERATIVO IA & RECONHECIMENTO DE VOZ (SPEECH-TO-TEXT)
  ========================================================================= */
  setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('Reconhecimento de fala não suportado neste navegador.');
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.lang = 'pt-BR';
    this.recognition.continuous = false;
    this.recognition.interimResults = false;

    this.recognition.onstart = () => {
      this.isListening = true;
      const micBtn = document.getElementById('btn-mic-input');
      const recBar = document.getElementById('voice-recording-indicator');
      if (micBtn) micBtn.classList.add('recording');
      if (recBar) recBar.classList.remove('hidden');
    };

    this.recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      console.log('Voz transcrita:', transcript);
      const input = document.getElementById('chat-text-input');
      if (input) input.value = transcript;
      this.handleChatSend();
    };

    this.recognition.onerror = (event) => {
      console.warn('Erro no reconhecimento de voz:', event.error);
      this.stopVoiceInput();
      this.showToast('Não foi possível captar sua voz. Tente falar novamente.');
    };

    this.recognition.onend = () => {
      this.stopVoiceInput();
    };
  }

  toggleVoiceInput() {
    if (!this.recognition) {
      this.showToast('Reconhecimento de voz não suportado neste navegador. Use a digitação.');
      return;
    }

    if (this.isListening) {
      this.recognition.stop();
      this.stopVoiceInput();
    } else {
      try {
        this.recognition.start();
      } catch (err) {
        console.warn('Erro ao iniciar reconhecimento:', err);
      }
    }
  }

  stopVoiceInput() {
    this.isListening = false;
    const micBtn = document.getElementById('btn-mic-input');
    const recBar = document.getElementById('voice-recording-indicator');
    if (micBtn) micBtn.classList.remove('recording');
    if (recBar) recBar.classList.add('hidden');
  }

  toggleVoiceReply() {
    this.voiceReplyActive = !this.voiceReplyActive;
    const toggleBtn = document.getElementById('btn-toggle-voice-reply');
    const label = document.getElementById('voice-reply-label');
    if (toggleBtn) {
      if (this.voiceReplyActive) {
        toggleBtn.classList.add('active');
        if (label) label.textContent = 'Voz Ativa';
        this.showToast('Respostas por voz ativadas.');
      } else {
        toggleBtn.classList.remove('active');
        if (label) label.textContent = 'Voz Mudo';
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        this.showToast('Respostas por voz silenciadas.');
      }
    }
  }

  async loadChatMessages() {
    const container = document.getElementById('chat-messages-container');
    if (!container) return;

    try {
      const res = await fetch('/api/chat/messages/');
      const data = await res.json();
      
      if (!data.messages || data.messages.length === 0) {
        container.innerHTML = `
          <div class="chat-bubble assistant">
            🌸 <strong>Oi, Rhaony! Eu sou a Bella</strong>, sua assistente pessoal inteligente. Como posso te ajudar hoje?
            <div style="font-size:0.75rem; color:var(--text-muted); margin-top:6px;">
              Dica: Experimente falar ou digitar <em>"Adicione reunião com o cliente às 15h"</em> ou <em>"Como está o clima em Itobi?"</em>.
            </div>
            <div class="chat-bubble-footer">
              <span>Agora</span>
            </div>
          </div>
        `;
        return;
      }

      container.innerHTML = '';
      data.messages.forEach(msg => this.renderChatMessage(msg, false));
      container.scrollTop = container.scrollHeight;
    } catch (err) {
      console.warn('Erro ao carregar mensagens:', err);
    }
  }

  sendQuickPrompt(promptText) {
    this.switchTab('chat');
    const input = document.getElementById('chat-text-input');
    if (input) input.value = promptText;
    this.handleChatSend();
  }

  async handleChatSend() {
    const input = document.getElementById('chat-text-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    const nowStr = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

    // Renderiza mensagem do usuário
    this.renderChatMessage({ role: 'user', content: text, created_at: nowStr });

    // Renderiza indicador de digitação
    const container = document.getElementById('chat-messages-container');
    const typingId = `typing-${Date.now()}`;
    if (container) {
      const typingDiv = document.createElement('div');
      typingDiv.id = typingId;
      typingDiv.className = 'chat-bubble assistant';
      typingDiv.innerHTML = '<span style="opacity:0.7;">Pensando e processando... ✨</span>';
      container.appendChild(typingDiv);
      container.scrollTop = container.scrollHeight;
    }

    try {
      const res = await fetch('/api/chat/send/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();

      // Remove typing
      const typingEl = document.getElementById(typingId);
      if (typingEl) typingEl.remove();

      if (data.status === 'success' && data.result) {
        const resObj = data.result;
        this.renderChatMessage({
          role: 'assistant',
          content: resObj.reply,
          action_type: resObj.action_type,
          action_executed: resObj.action_executed,
          created_at: resObj.created_at || nowStr
        });

        // Se uma ação foi executada (ex: novo evento), atualiza os dados em tempo real
        if (resObj.action_executed) {
          if (resObj.action_executed.type === 'event_created') {
            this.showToast(`📅 "${resObj.action_executed.title}" adicionado à sua agenda!`);
            this.loadTodayBriefing();
          } else if (resObj.action_executed.type === 'email_created') {
            this.showToast(`✉️ "${resObj.action_executed.subject}" registrado nos e-mails!`);
            this.loadTodayBriefing();
          }
        }

        // Fala a resposta por voz se habilitado
        if (this.voiceReplyActive && resObj.reply) {
          this.speakText(resObj.reply);
        }
      } else {
        this.renderChatMessage({
          role: 'assistant',
          content: 'Desculpe, ocorreu uma instabilidade ao processar a resposta.',
          created_at: nowStr
        });
      }
    } catch (err) {
      console.error(err);
      const typingEl = document.getElementById(typingId);
      if (typingEl) typingEl.remove();
      this.renderChatMessage({
        role: 'assistant',
        content: 'Não foi possível conectar com o servidor no momento.',
        created_at: nowStr
      });
    }
  }

  renderChatMessage(msg, autoScroll = true) {
    const container = document.getElementById('chat-messages-container');
    if (!container) return;

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${msg.role}`;

    let actionBadgeHtml = '';
    if (msg.action_executed) {
      if (msg.action_executed.type === 'event_created') {
        actionBadgeHtml = `
          <div class="action-pill-card">
            <span>📅</span>
            <strong>Compromisso salvo na Agenda (${msg.action_executed.time || 'Hoje'})</strong>
          </div>
        `;
      } else if (msg.action_executed.type === 'email_created') {
        actionBadgeHtml = `
          <div class="action-pill-card">
            <span>✉️</span>
            <strong>E-mail salvo com prioridade</strong>
          </div>
        `;
      }
    }

    const isAssistant = msg.role === 'assistant';
    const cleanContent = this.formatMarkdown(msg.content);

    bubble.innerHTML = `
      <div>${cleanContent}</div>
      ${actionBadgeHtml}
      <div class="chat-bubble-footer">
        ${isAssistant ? `
          <button class="chat-play-audio-btn" onclick="app.speakText('${msg.content.replace(/'/g, "\\'").replace(/\n/g, ' ')}')">
            🔊 Ouvir
          </button>
        ` : ''}
        <span>${msg.created_at || 'Hoje'}</span>
      </div>
    `;

    container.appendChild(bubble);
    if (autoScroll) {
      container.scrollTop = container.scrollHeight;
    }
  }

  speakText(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();

    const clean = text
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/#/g, '')
      .replace(/•/g, '')
      .replace(/\n+/g, '. ');

    const utterance = new SpeechSynthesisUtterance(clean);
    this.configureBellaUtterance(utterance);
    window.speechSynthesis.speak(utterance);
  }

  /* =========================================================================
     MODO ÁUDIO INTERATIVO CONTÍNUO (HANDS-FREE CONVERSATIONAL AI)
  ========================================================================= */
  setupContinuousVoice() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn('SpeechRecognition não suportado neste navegador.');
      return;
    }

    this.continuousRecognition = new SpeechRec();
    this.continuousRecognition.lang = 'pt-BR';
    this.continuousRecognition.continuous = false; // Ciclos dinâmicos para máxima estabilidade mobile
    this.continuousRecognition.interimResults = true;

    this.continuousRecognition.onstart = () => {
      if (this.continuousVoiceActive && !this.continuousVoicePaused && !this.isAssistantSpeakingLive) {
        this.setLiveVoiceStatus('listening');
      }
    };

    this.continuousRecognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      const userTextEl = document.getElementById('voice-live-user-text');
      if (userTextEl) {
        userTextEl.textContent = `"${finalTranscript || interimTranscript || 'Ouvindo...'}"`;
      }

      if (finalTranscript && finalTranscript.trim()) {
        this.handleLiveVoiceUtterance(finalTranscript.trim());
      }
    };

    this.continuousRecognition.onerror = (event) => {
      console.warn('Live Speech error:', event.error);
      if (event.error === 'not-allowed') {
        this.showToast('Permissão de microfone negada.');
        this.stopContinuousVoiceMode();
        return;
      }
      if (this.continuousVoiceActive && !this.continuousVoicePaused && !this.isAssistantSpeakingLive) {
        setTimeout(() => this.startLiveListening(), 600);
      }
    };

    this.continuousRecognition.onend = () => {
      if (this.continuousVoiceActive && !this.continuousVoicePaused && !this.isAssistantSpeakingLive) {
        setTimeout(() => this.startLiveListening(), 300);
      }
    };
  }

  startContinuousVoiceMode() {
    this.continuousVoiceActive = true;
    this.continuousVoicePaused = false;
    this.isAssistantSpeakingLive = false;

    const modal = document.getElementById('modal-voice-live');
    if (modal) modal.classList.remove('hidden');

    const toggleBtn = document.getElementById('btn-voice-live-toggle');
    if (toggleBtn) toggleBtn.innerHTML = '<span>⏸️ Pausar</span>';

    const userTextEl = document.getElementById('voice-live-user-text');
    if (userTextEl) userTextEl.textContent = '"Aguardando você falar..."';

    const aiTextEl = document.getElementById('voice-live-ai-text');
    if (aiTextEl) aiTextEl.textContent = 'Olá! Modo de voz contínuo ativado. Pode falar livremente.';

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      this.setLiveVoiceStatus('paused');
      const pill = document.getElementById('voice-live-status-pill');
      if (pill) pill.textContent = '⚠️ Microfone não suportado no navegador (Simulação ativa)';
      this.speakLiveUtterance('Olá! Modo de voz ativado. Seu navegador não possui microfone nativo, mas você pode usar o chat.');
      return;
    }

    // Saudação inicial por voz
    this.speakLiveUtterance('Olá! Modo de voz contínuo ativado. Como posso te ajudar agora?', () => {
      if (this.continuousVoiceActive && !this.continuousVoicePaused) {
        this.startLiveListening();
      }
    });
  }

  startLiveListening() {
    if (!this.continuousRecognition || !this.continuousVoiceActive || this.continuousVoicePaused || this.isAssistantSpeakingLive) {
      return;
    }
    try {
      this.setLiveVoiceStatus('listening');
      this.continuousRecognition.start();
    } catch (e) {
      // Ignora erro se já estiver ativo
    }
  }

  stopLiveListening() {
    if (this.continuousRecognition) {
      try {
        this.continuousRecognition.stop();
      } catch (e) {}
    }
  }

  async handleLiveVoiceUtterance(text) {
    this.stopLiveListening();
    const lower = text.toLowerCase();

    // Comandos de encerramento por voz
    if (lower.includes('encerrar') || lower.includes('fechar') || lower.includes('tchau') || lower.includes('sair do modo') || lower.includes('parar conversa')) {
      this.speakLiveUtterance('Até logo! Encerrando modo de conversa por voz.', () => {
        this.stopContinuousVoiceMode();
      });
      return;
    }

    this.setLiveVoiceStatus('thinking');
    const aiTextEl = document.getElementById('voice-live-ai-text');
    if (aiTextEl) aiTextEl.textContent = 'Consultando IA e processando seu pedido... ✨';

    try {
      const res = await fetch('/api/chat/send/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();

      if (data.status === 'success' && data.result) {
        const reply = data.result.reply;
        if (aiTextEl) aiTextEl.textContent = reply;

        // Se gerou ação (compromisso ou tarefa), executa toasts e atualiza painéis
        if (data.result.action_executed) {
          const act = data.result.action_executed;
          if (act.type === 'event_created') {
            this.showToast(`📅 "${act.title}" adicionado à agenda!`);
            this.loadTodayBriefing();
          } else if (act.type === 'task_created') {
            this.showToast(`🎯 Tarefa "${act.title}" criada!`);
            this.loadTasks();
          } else if (act.type === 'email_created') {
            this.showToast(`✉️ "${act.subject}" registrado nos e-mails!`);
            this.loadTodayBriefing();
          }
        }

        // Fala a resposta do assistente e retoma escuta ao término
        this.speakLiveUtterance(reply, () => {
          if (this.continuousVoiceActive && !this.continuousVoicePaused) {
            this.startLiveListening();
          }
        });
      } else {
        if (aiTextEl) aiTextEl.textContent = 'Desculpe, tive uma instabilidade. Pode repetir?';
        this.speakLiveUtterance('Desculpe, tive uma instabilidade. Pode repetir?', () => {
          if (this.continuousVoiceActive && !this.continuousVoicePaused) {
            this.startLiveListening();
          }
        });
      }
    } catch (err) {
      console.error(err);
      if (aiTextEl) aiTextEl.textContent = 'Erro ao conectar ao servidor.';
      this.speakLiveUtterance('Ocorreu um erro de conexão. Tente novamente em alguns instantes.', () => {
        if (this.continuousVoiceActive && !this.continuousVoicePaused) {
          this.startLiveListening();
        }
      });
    }
  }

  speakLiveUtterance(text, onComplete) {
    if (!('speechSynthesis' in window)) {
      if (onComplete) onComplete();
      return;
    }

    window.speechSynthesis.cancel();
    this.isAssistantSpeakingLive = true;
    this.setLiveVoiceStatus('speaking');

    const clean = text
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/#/g, '')
      .replace(/•/g, '')
      .replace(/\n+/g, '. ');

    const utterance = new SpeechSynthesisUtterance(clean);
    this.configureBellaUtterance(utterance);

    utterance.onend = () => {
      this.isAssistantSpeakingLive = false;
      if (onComplete) onComplete();
    };

    utterance.onerror = (e) => {
      console.warn('Erro ao falar voz ao vivo:', e);
      this.isAssistantSpeakingLive = false;
      if (onComplete) onComplete();
    };

    window.speechSynthesis.speak(utterance);
  }

  setLiveVoiceStatus(state) {
    const orb = document.getElementById('voice-main-orb');
    const pill = document.getElementById('voice-live-status-pill');

    if (orb) {
      orb.className = `voice-main-orb state-${state}`;
    }

    if (pill) {
      pill.className = `voice-status-pill state-${state}`;
      if (state === 'listening') {
        pill.textContent = '🟢 Ouvindo você... Fale naturalmente';
      } else if (state === 'thinking') {
        pill.textContent = '🟡 Processando com IA...';
      } else if (state === 'speaking') {
        pill.textContent = '🟣 Assistente falando...';
      } else if (state === 'paused') {
        pill.textContent = '⏸️ Conversa Pausada';
      }
    }
  }

  toggleContinuousVoicePause() {
    this.continuousVoicePaused = !this.continuousVoicePaused;
    const btn = document.getElementById('btn-voice-live-toggle');

    if (this.continuousVoicePaused) {
      this.stopLiveListening();
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      this.isAssistantSpeakingLive = false;
      this.setLiveVoiceStatus('paused');
      if (btn) btn.innerHTML = '<span>▶️ Retomar</span>';
      this.showToast('Conversa por voz pausada.');
    } else {
      if (btn) btn.innerHTML = '<span>⏸️ Pausar</span>';
      this.showToast('Conversa por voz retomada.');
      this.startLiveListening();
    }
  }

  stopContinuousVoiceMode() {
    this.continuousVoiceActive = false;
    this.continuousVoicePaused = false;
    this.isAssistantSpeakingLive = false;

    this.stopLiveListening();
    if (window.speechSynthesis) window.speechSynthesis.cancel();

    const modal = document.getElementById('modal-voice-live');
    if (modal) modal.classList.add('hidden');

    this.showToast('Modo de voz encerrado.');
  }

  /* =========================================================================
     MULTI-CURRENCY: USD / EUR / BTC
  ========================================================================= */
  async loadMultiCurrency() {
    try {
      const res = await fetch('/api/currency/multi/');
      if (!res.ok) return;
      const data = await res.json();
      this.renderMultiCurrency(data.rates || []);
    } catch (e) {
      console.warn('Erro ao carregar cotações múltiplas:', e);
    }
  }

  renderMultiCurrency(rates) {
    const container = document.getElementById('multi-currency-rates');
    if (!container) return;

    if (!rates.length) {
      container.innerHTML = '<p class="empty-state-msg">Cotações indisponíveis no momento.</p>';
      return;
    }

    container.innerHTML = rates.map(r => {
      const isPositive = r.positive;
      const bidFormatted = r.code === 'BTC'
        ? `R$ ${Number(r.bid).toLocaleString('pt-BR')}`
        : `R$ ${Number(r.bid).toFixed(2).replace('.', ',')}`;

      return `
        <div class="rate-row">
          <div class="rate-row-left">
            <div class="rate-symbol-badge">${r.symbol}</div>
            <div class="rate-info">
              <span class="rate-name">${r.name} / BRL</span>
              <span class="rate-bid">${bidFormatted}</span>
            </div>
          </div>
          <span class="rate-variation ${isPositive ? 'positive' : 'negative'}">
            ${r.variation}
          </span>
        </div>
      `;
    }).join('');

    // Atualiza conversor usando USD
    const usdRate = rates.find(r => r.code === 'USD');
    if (usdRate) {
      this._usdBid = usdRate.bid;
      this.updateConverter();
    }
  }

  updateConverter() {
    const input = document.getElementById('quick-usd-input');
    const result = document.getElementById('quick-brl-result');
    if (!input || !result) return;
    const usd = parseFloat(input.value) || 0;
    const rate = this._usdBid || 5.06;
    result.textContent = (usd * rate).toFixed(2).replace('.', ',');
  }

  /* =========================================================================
     WEEKLY FORECAST: SPARKLINE 7 DIAS
  ========================================================================= */
  async loadWeeklyForecast() {
    try {
      const res = await fetch('/api/weather/weekly/');
      if (!res.ok) return;
      const data = await res.json();
      this.renderWeeklyForecast(data.forecast || []);
    } catch (e) {
      console.warn('Erro ao carregar previsão semanal:', e);
    }
  }

  renderWeeklyForecast(days) {
    const container = document.getElementById('weekly-forecast-chart');
    if (!container || !days.length) return;

    const today = new Date().toISOString().slice(0, 10);

    // Gera as colunas de dias
    const daysHtml = days.map((d, i) => {
      const isToday = d.date === today;
      return `
        <div class="weekly-day-col ${isToday ? 'today-col' : ''}">
          <span class="day-label ${isToday ? 'day-today-label' : ''}">${isToday ? 'Hoje' : d.weekday}</span>
          <span class="day-icon">${d.icon}</span>
          <span class="day-temp-max">${d.temp_max}°</span>
          <span class="day-temp-min">${d.temp_min}°</span>
          <span class="day-rain">💧${d.rain_prob}%</span>
        </div>
      `;
    }).join('');

    // Gera sparkline SVG das temperaturas máximas
    const maxTemps = days.map(d => d.temp_max);
    const minTemps = days.map(d => d.temp_min);
    const allTemps = [...maxTemps, ...minTemps];
    const minT = Math.min(...allTemps) - 2;
    const maxT = Math.max(...allTemps) + 2;
    const svgW = 300;
    const svgH = 50;
    const pad = 10;
    const step = (svgW - pad * 2) / (days.length - 1);

    const normY = (t) => svgH - pad - ((t - minT) / (maxT - minT)) * (svgH - pad * 2);

    const maxPoints = maxTemps.map((t, i) => `${pad + i * step},${normY(t)}`).join(' ');
    const minPoints = minTemps.map((t, i) => `${pad + i * step},${normY(t)}`).join(' ');

    const sparkSvg = `
      <div class="sparkline-svg-wrap">
        <svg viewBox="0 0 ${svgW} ${svgH}" xmlns="http://www.w3.org/2000/svg">
          <polyline points="${minPoints}" fill="none" stroke="rgba(96,165,250,0.5)" stroke-width="1.5" stroke-linejoin="round"/>
          <polyline points="${maxPoints}" fill="none" stroke="rgba(251,191,36,0.8)" stroke-width="2" stroke-linejoin="round"/>
          ${maxTemps.map((t, i) => `<circle cx="${pad + i * step}" cy="${normY(t)}" r="3" fill="#fbbf24" opacity="0.9"/>`).join('')}
        </svg>
      </div>
    `;

    container.innerHTML = `
      <div class="weekly-days-row">${daysHtml}</div>
      ${sparkSvg}
    `;
  }

  /* =========================================================================
     TASKS WIDGET - PRODUTIVIDADE
  ========================================================================= */
  async loadTasks() {
    try {
      const res = await fetch('/api/tasks/');
      if (!res.ok) return;
      const data = await res.json();
      this.renderTasks(data.tasks || [], data.total || 0, data.done || 0);
    } catch (e) {
      console.warn('Erro ao carregar tarefas:', e);
    }
  }

  renderTasks(tasks, total, done) {
    const listEl = document.getElementById('tasks-list');
    const progressBar = document.getElementById('tasks-progress-bar');
    const progressLabel = document.getElementById('tasks-progress-label');

    // Atualiza progress bar
    if (progressBar) {
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
      progressBar.style.width = pct + '%';
    }
    if (progressLabel) {
      progressLabel.textContent = `${done}/${total}`;
    }

    if (!listEl) return;

    if (!tasks.length) {
      listEl.innerHTML = '<p class="empty-state-msg">Nenhuma tarefa para hoje. Adicione abaixo! ✨</p>';
      return;
    }

    listEl.innerHTML = tasks.map(t => `
      <div class="task-item priority-${t.priority} ${t.is_done ? 'is-done' : ''}" data-id="${t.id}">
        <div class="task-checkbox" onclick="app.toggleTask(${t.id}, ${!t.is_done})"></div>
        <div class="task-content">
          <div class="task-title">${this.escapeHtml(t.title)}</div>
          <div class="task-meta">
            <span class="task-cat-badge">${t.category_label}</span>
          </div>
        </div>
        <button class="task-delete-btn" onclick="app.deleteTask(${t.id})" title="Remover">✕</button>
      </div>
    `).join('');
  }

  async toggleTask(taskId, newDone) {
    try {
      const res = await fetch(`/api/tasks/${taskId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_done: newDone }),
      });
      if (res.ok) {
        await this.loadTasks();
        this.showToast(newDone ? '✅ Tarefa concluída!' : '↩️ Tarefa reaberta');
      }
    } catch (e) {
      this.showToast('Erro ao atualizar tarefa.');
    }
  }

  async deleteTask(taskId) {
    try {
      await fetch(`/api/tasks/${taskId}/`, { method: 'DELETE' });
      await this.loadTasks();
      this.showToast('🗑️ Tarefa removida');
    } catch (e) {
      this.showToast('Erro ao remover tarefa.');
    }
  }

  async addQuickTask() {
    const input = document.getElementById('quick-task-input');
    const prioritySelect = document.getElementById('quick-task-priority');
    if (!input || !input.value.trim()) return;

    const title = input.value.trim();
    const priority = prioritySelect ? prioritySelect.value : 'medium';

    try {
      const res = await fetch('/api/tasks/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, priority, category: 'work' }),
      });
      if (res.ok) {
        input.value = '';
        await this.loadTasks();
        this.showToast('🎯 Tarefa adicionada!');
      }
    } catch (e) {
      this.showToast('Erro ao adicionar tarefa.');
    }
  }

  setupTasksQuickAdd() {
    const input = document.getElementById('quick-task-input');
    const btn = document.getElementById('btn-add-quick-task');

    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.addQuickTask();
        }
      });
    }
    if (btn) {
      btn.addEventListener('click', () => this.addQuickTask());
    }
  }

  /* =========================================================================
     PUSH NOTIFICATIONS NATIVAS + AUTO-REFRESH
  ========================================================================= */
  async requestPushPermission() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default') {
      const perm = await Notification.requestPermission();
      if (perm === 'granted') {
        this.showToast('🔔 Notificações ativadas! Você receberá o resumo diário.');
      }
    }
  }

  sendLocalNotification(title, body) {
    if (Notification.permission === 'granted') {
      new Notification(title, {
        body,
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-192.png',
      });
    }
  }

  setupAutoRefresh() {
    // Auto-refresh a cada 30 minutos
    setInterval(async () => {
      await this.loadMultiCurrency();
      await this.loadWeeklyForecast();
      await this.loadTasks();
      console.log('Auto-refresh executado às', new Date().toLocaleTimeString('pt-BR'));
    }, 30 * 60 * 1000);
  }

  /* =========================================================================
     VOZ DA BELLA (SÍNTESE DE VOZ FEMININA JOVEM & PERSONALIZÁVEL)
  ========================================================================= */
  setupBellaVoice() {
    if (!('speechSynthesis' in window)) return;

    // Atualiza sliders com valores salvos
    const pitchSlider = document.getElementById('bella-voice-pitch');
    const rateSlider = document.getElementById('bella-voice-rate');
    const pitchVal = document.getElementById('val-voice-pitch');
    const rateVal = document.getElementById('val-voice-rate');

    if (pitchSlider) pitchSlider.value = this.bellaPitch;
    if (rateSlider) rateSlider.value = this.bellaRate;
    if (pitchVal) pitchVal.textContent = `${this.bellaPitch.toFixed(2)}x`;
    if (rateVal) rateVal.textContent = `${this.bellaRate.toFixed(2)}x`;

    // Carrega vozes imediatamente ou via evento
    this.populateBellaVoiceSelect();
    window.speechSynthesis.onvoiceschanged = () => {
      this.populateBellaVoiceSelect();
    };
  }

  getBellaVoice() {
    if (!('speechSynthesis' in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) return null;

    // 1. Se o usuário escolheu uma voz específica
    if (this.selectedVoiceName) {
      const chosen = voices.find(v => v.name === this.selectedVoiceName);
      if (chosen) return chosen;
    }

    // 2. Prioridade para vozes femininas naturais em pt-BR de alta qualidade
    // Microsoft Francisca Online (Natural) e Google português do Brasil são super jovens e naturais
    const priorityFemaleNames = [
      'francisca', 'leticia', 'letícia', 'luciana', 'vitória', 'vitoria', 
      'heloisa', 'heloísa', 'maria', 'camila', 'fernanda', 'joana', 
      'google português do brasil', 'brazil female'
    ];

    for (const name of priorityFemaleNames) {
      const match = voices.find(v => 
        (v.lang.includes('pt') || v.lang.includes('PT')) && 
        v.name.toLowerCase().includes(name)
      );
      if (match) return match;
    }

    // 3. Qualquer voz pt-BR feminina ou com tag feminina
    const anyFemalePt = voices.find(v => 
      (v.lang === 'pt-BR' || v.lang.startsWith('pt')) && 
      (v.name.toLowerCase().includes('female') || v.name.toLowerCase().includes('mulher'))
    );
    if (anyFemalePt) return anyFemalePt;

    // 4. Qualquer voz pt-BR
    const ptVoice = voices.find(v => v.lang === 'pt-BR' || v.lang.startsWith('pt'));
    return ptVoice || null;
  }

  configureBellaUtterance(utterance) {
    utterance.lang = 'pt-BR';
    const bellaVoice = this.getBellaVoice();
    if (bellaVoice) {
      utterance.voice = bellaVoice;
    }
    // Tom jovial doce e velocidade moderna
    utterance.pitch = this.bellaPitch || 1.18;
    utterance.rate = this.bellaRate || 1.06;
  }

  populateBellaVoiceSelect() {
    const select = document.getElementById('bella-voice-select');
    if (!select || !('speechSynthesis' in window)) return;

    const voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) return;

    const ptVoices = voices.filter(v => v.lang.startsWith('pt') || v.lang.includes('BR'));
    const activeVoice = this.getBellaVoice();

    select.innerHTML = '';
    
    // Lista vozes em português primeiro
    if (ptVoices.length > 0) {
      ptVoices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.name;
        const isFemale = /francisca|leticia|letícia|luciana|maria|vitória|vitoria|heloisa|camila|fernanda|joana|google|female|mulher/i.test(v.name);
        opt.textContent = `${isFemale ? '🌸 ' : '🎙️ '}${v.name} (${v.lang})`;
        if (activeVoice && activeVoice.name === v.name) {
          opt.selected = true;
        }
        select.appendChild(opt);
      });
    } else {
      // Se não houver voz pt explícita no momento
      voices.slice(0, 10).forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.name;
        opt.textContent = `${v.name} (${v.lang})`;
        select.appendChild(opt);
      });
    }
  }

  onVoiceSelectChange(voiceName) {
    this.selectedVoiceName = voiceName;
    localStorage.setItem('bella_voice_name', voiceName);
    this.showToast('Voz da Bella atualizada!');
    this.testBellaVoice();
  }

  onPitchChange(val) {
    this.bellaPitch = parseFloat(val);
    localStorage.setItem('bella_voice_pitch', val);
    const label = document.getElementById('val-voice-pitch');
    if (label) label.textContent = `${this.bellaPitch.toFixed(2)}x`;
  }

  onRateChange(val) {
    this.bellaRate = parseFloat(val);
    localStorage.setItem('bella_voice_rate', val);
    const label = document.getElementById('val-voice-rate');
    if (label) label.textContent = `${this.bellaRate.toFixed(2)}x`;
  }

  testBellaVoice() {
    if (!('speechSynthesis' in window)) {
      this.showToast('Síntese de voz não suportada pelo seu navegador.');
      return;
    }
    window.speechSynthesis.cancel();

    const sampleText = "Oi, Rhaony! Eu sou a Bella, sua assistente pessoal! Minha voz já está configurada como você pediu. Como posso te ajudar hoje?";
    const utterance = new SpeechSynthesisUtterance(sampleText);
    this.configureBellaUtterance(utterance);

    utterance.onstart = () => {
      this.showToast('🌸 Bella falando...');
    };

    window.speechSynthesis.speak(utterance);
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }
}

// Inicializa a aplicação globalmente
const app = new PersonalAssistantApp();
