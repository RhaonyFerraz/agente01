import os
import requests
import datetime
from django.utils import timezone
from django.conf import settings
from .models import CalendarEvent, EmailHighlight, DailyBriefing, UserPreference, ChatMessage, QuickTask

# Tabela de interpretação dos códigos WMO de tempo da Open-Meteo
WMO_WEATHER_CODES = {
    0: ("Ensolarado / Céu Limpo", "☀️"),
    1: ("Predominantemente Ensolarado", "🌤️"),
    2: ("Parcialmente Nublado", "⛅"),
    3: ("Nublado", "☁️"),
    45: ("Nevoeiro", "🌫️"),
    48: ("Nevoeiro com Geada", "🌫️"),
    51: ("Garoa Leve", "🌦️"),
    53: ("Garoa Moderada", "🌦️"),
    55: ("Garoa Densa", "🌧️"),
    61: ("Chuva Fraca", "🌧️"),
    63: ("Chuva Moderada", "🌧️"),
    65: ("Chuva Forte", "🌧️"),
    80: ("Pancadas de Chuva Leves", "🌦️"),
    81: ("Pancadas de Chuva Moderadas", "🌧️"),
    82: ("Pancadas de Chuva Violentas", "⛈️"),
    95: ("Trovoada / Tempestade", "⛈️"),
    96: ("Tempestade com Granizo Leve", "⛈️"),
    99: ("Tempestade com Granizo Forte", "⛈️"),
}


class WeatherService:
    @staticmethod
    def get_weather(lat=None, lon=None, city="Itobi, SP"):
        """Obtém previsão do tempo em tempo real via Open-Meteo (API gratuita e precisa)"""
        latitude = lat or settings.DEFAULT_LAT
        longitude = lon or settings.DEFAULT_LON
        
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "America/Sao_Paulo"
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                current = data.get("current", {})
                daily = data.get("daily", {})
                
                weather_code = current.get("weather_code", 0)
                condition_desc, icon = WMO_WEATHER_CODES.get(weather_code, ("Tempo Estável", "⛅"))
                
                temp_max = daily.get("temperature_2m_max", [26.0])[0]
                temp_min = daily.get("temperature_2m_min", [18.0])[0]
                rain_prob = daily.get("precipitation_probability_max", [40])[0]
                
                return {
                    "city": city,
                    "current_temp": round(current.get("temperature_2m", 22.0), 1),
                    "temp_min": round(temp_min, 1),
                    "temp_max": round(temp_max, 1),
                    "condition": condition_desc,
                    "icon": icon,
                    "rain_prob": rain_prob,
                    "humidity": current.get("relative_humidity_2m", 65),
                    "wind_speed": current.get("wind_speed_10m", 12)
                }
        except Exception as e:
            print(f"Erro ao buscar clima: {e}")
            
        # Fallback seguro
        return {
            "city": city,
            "current_temp": 23.5,
            "temp_min": 18.0,
            "temp_max": 26.0,
            "condition": "Céu parcialmente nublado com chance de pancadas de chuva",
            "icon": "⛅",
            "rain_prob": 50,
            "humidity": 70,
            "wind_speed": 10
        }


class CurrencyService:
    @staticmethod
    def get_usd_rate():
        """Obtém cotação comercial do Dólar Americano (USD/BRL) via AwesomeAPI"""
        url = "https://economia.awesomeapi.com.br/last/USD-BRL"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json().get("USDBRL", {})
                bid = float(data.get("bid", 5.06))
                ask = float(data.get("ask", 5.07))
                pct = float(data.get("pctChange", 0.0))
                high = float(data.get("high", bid))
                low = float(data.get("low", bid))
                
                return {
                    "code": "USD",
                    "name": "Dólar Americano / Real",
                    "bid": round(bid, 4),
                    "ask": round(ask, 4),
                    "high": round(high, 4),
                    "low": round(low, 4),
                    "variation": f"{pct:+.2f}%",
                    "updated_at": data.get("create_date", timezone.now().strftime("%Y-%m-%d %H:%M:%S"))
                }
        except Exception as e:
            print(f"Erro ao buscar cotação: {e}")
            
        return {
            "code": "USD",
            "name": "Dólar Americano / Real",
            "bid": 5.0627,
            "ask": 5.0631,
            "high": 5.0980,
            "low": 5.0613,
            "variation": "-0.69%",
            "updated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def get_multi_rates():
        """Obtém cotações de USD, EUR e BTC em BRL simultaneamente via AwesomeAPI"""
        pairs = "USD-BRL,EUR-BRL,BTC-BRL"
        url = f"https://economia.awesomeapi.com.br/last/{pairs}"
        defaults = {
            "USDBRL": {"code": "USD", "name": "Dólar", "symbol": "$", "bid": 5.0627, "pctChange": -0.69},
            "EURBRL": {"code": "EUR", "name": "Euro", "symbol": "€", "bid": 5.5340, "pctChange": +0.23},
            "BTCBRL": {"code": "BTC", "name": "Bitcoin", "symbol": "₿", "bid": 320000.0, "pctChange": +2.10},
        }
        try:
            response = requests.get(url, timeout=6)
            if response.status_code == 200:
                raw = response.json()
                result = []
                for key, fallback in defaults.items():
                    d = raw.get(key, {})
                    bid = float(d.get("bid", fallback["bid"]))
                    pct = float(d.get("pctChange", fallback["pctChange"]))
                    result.append({
                        "code": fallback["code"],
                        "name": fallback["name"],
                        "symbol": fallback["symbol"],
                        "bid": round(bid, 2 if fallback["code"] != "BTC" else 0),
                        "variation": f"{pct:+.2f}%",
                        "positive": pct >= 0,
                    })
                return result
        except Exception as e:
            print(f"Erro ao buscar múltiplas cotações: {e}")

        return [
            {"code": "USD", "name": "Dólar", "symbol": "$", "bid": 5.06, "variation": "-0.69%", "positive": False},
            {"code": "EUR", "name": "Euro", "symbol": "€", "bid": 5.53, "variation": "+0.23%", "positive": True},
            {"code": "BTC", "name": "Bitcoin", "symbol": "₿", "bid": 320000, "variation": "+2.10%", "positive": True},
        ]


class WeeklyForecastService:
    """Serviço de previsão climática semanal (7 dias) para gráfico sparkline"""
    @staticmethod
    def get_weekly(lat=None, lon=None):
        """Retorna previsão de 7 dias com temperaturas máximas e mínimas"""
        latitude = lat or settings.DEFAULT_LAT
        longitude = lon or settings.DEFAULT_LON
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "America/Sao_Paulo",
            "forecast_days": 7,
        }
        try:
            resp = requests.get(url, params=params, timeout=6)
            if resp.status_code == 200:
                data = resp.json().get("daily", {})
                dates = data.get("time", [])
                temps_max = data.get("temperature_2m_max", [])
                temps_min = data.get("temperature_2m_min", [])
                rain_probs = data.get("precipitation_probability_max", [])
                codes = data.get("weather_code", [])
                days = []
                for i, d in enumerate(dates):
                    dt = datetime.datetime.strptime(d, "%Y-%m-%d")
                    code = codes[i] if i < len(codes) else 0
                    _, icon = WMO_WEATHER_CODES.get(code, ("", "⛅"))
                    days.append({
                        "date": d,
                        "weekday": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][dt.weekday()],
                        "temp_max": round(temps_max[i], 1) if i < len(temps_max) else 26.0,
                        "temp_min": round(temps_min[i], 1) if i < len(temps_min) else 18.0,
                        "rain_prob": rain_probs[i] if i < len(rain_probs) else 40,
                        "icon": icon,
                    })
                return days
        except Exception as e:
            print(f"Erro previsão semanal: {e}")

        # Fallback
        today = datetime.date.today()
        return [
            {"date": str(today + datetime.timedelta(days=i)),
             "weekday": ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"][(today.weekday() + iclass WebSearchService:
    """Serviço gratuito de pesquisa na web em tempo real (DuckDuckGo + Google News RSS)"""

    @staticmethod
    def search_news(query="noticias brasil economia tecnologia", max_results=5):
        """Busca notícias recentes em tempo real via Google News RSS (100% gratuito e atualizado)"""
        import urllib.parse
        import xml.etree.ElementTree as ET
        import re

        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        results = []
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                items = root.findall('.//item')[:max_results]
                for it in items:
                    title_elem = it.find('title')
                    link_elem = it.find('link')
                    desc_elem = it.find('description')
                    pub_elem = it.find('pubDate')

                    full_title = title_elem.text if title_elem is not None else ""
                    source_name = "Notícias"
                    clean_title = full_title
                    if " - " in full_title:
                        parts = full_title.rsplit(" - ", 1)
                        clean_title = parts[0].strip()
                        source_name = parts[1].strip()

                    raw_desc = desc_elem.text if desc_elem is not None else ""
                    clean_desc = re.sub(r'<[^>]+>', '', raw_desc).strip()

                    link = link_elem.text if link_elem is not None else ""
                    pub_date = pub_elem.text if pub_elem is not None else ""

                    results.append({
                        "title": clean_title,
                        "source": source_name,
                        "snippet": clean_desc or clean_title,
                        "url": link,
                        "published_at": pub_date
                    })
        except Exception as e:
            print(f"Erro ao buscar notícias RSS: {e}")

        # Se o RSS falhar, tenta via ddgs
        if not results:
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    ddg_news = list(ddgs.news(query, region="pt-br", max_results=max_results))
                    for n in ddg_news:
                        results.append({
                            "title": n.get("title", ""),
                            "source": n.get("source", "Web"),
                            "snippet": n.get("body", ""),
                            "url": n.get("url", ""),
                            "published_at": n.get("date", "")
                        })
            except Exception as e:
                print(f"Erro fallback ddgs news: {e}")

        return results

    @staticmethod
    def search_web(query, max_results=4):
        """Busca em tempo real na internet via DuckDuckGo (DDGS)"""
        if not query or not query.strip():
            return []

        clean_q = query.strip()
        results = []
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                ddg_res = list(ddgs.text(clean_q, region="pt-br", max_results=max_results))
                for item in ddg_res:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("body", ""),
                        "url": item.get("href", "")
                    })
        except Exception as e:
            print(f"Erro na busca web DDGS: {e}")

        # Se não houver resultados na busca geral, tenta via notícias RSS
        if not results:
            news_res = WebSearchService.search_news(clean_q, max_results=max_results)
            for n in news_res:
                results.append({
                    "title": n.get("title", ""),
                    "snippet": n.get("snippet", ""),
                    "url": n.get("url", "")
                })

        return results


class GeminiService:
    @staticmethod
    def generate_briefing(weather, currency, agenda_events, email_highlights, news_items=None, custom_api_key=None):
        """Gera o resumo executivo inteligente usando Google Gemini AI (Google AI Studio)"""
        api_key = custom_api_key or os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
        
        # Formata dados para o prompt
        events_str = ""
        if agenda_events:
            for ev in agenda_events:
                hora = timezone.localtime(ev.start_time).strftime("%H:%M")
                events_str += f"- {hora}: {ev.title} ({ev.get_category_display()}) {'[PRIORIDADE ALTA]' if ev.is_important else ''}\n"
        else:
            events_str = "- Nenhum compromisso registrado para hoje até o momento.\n"
            
        emails_str = ""
        if email_highlights:
            for em in email_highlights:
                emails_str += f"- De: {em.sender} | Assunto: {em.subject} {'[IMPORTANTE]' if em.is_important else ''}\n  Resumo: {em.snippet}\n"
        else:
            emails_str = "- Nenhum e-mail urgente ou não lido pendente.\n"

        news_str = ""
        if news_items:
            for n in news_items[:3]:
                news_str += f"- {n.get('title')} ({n.get('source', 'Notícias')})\n"
        else:
            news_str = "- Sem notícias extraordinárias no momento.\n"

        prompt = f"""Você é a Bella, uma assistente pessoal inteligente, jovem, carismática, alegre, empática e prestativa. Você fala de forma natural, moderna e agradável, em português brasileiro, com tom de uma moça jovem e profissional.

Dados atuais do dia:
1. CLIMA EM {weather['city'].upper()}:
- Temperatura Mínima: {weather['temp_min']}°C
- Temperatura Máxima: {weather['temp_max']}°C
- Temperatura Atual: {weather['current_temp']}°C
- Condições: {weather['condition']}
- Probabilidade de chuva: {weather['rain_prob']}%

2. COTAÇÃO DO DÓLAR AMERICANO (USD/BRL):
- Cotação Comercial de Compra: R$ {currency['bid']}
- Cotação Comercial de Venda: R$ {currency['ask']}
- Variação do dia: {currency['variation']}

3. AGENDA DE HOJE (Ordem Cronológica):
{events_str}

4. E-MAILS E DESTAQUES:
{emails_str}

5. PRINCIPAIS NOTÍCIAS DO MOMENTO (EM TEMPO REAL):
{news_str}

INSTRUÇÕES OBRIGATÓRIAS DE RESPOSTA E TOM DE VOZ:
- Saudação: Cumprimente de forma cortez, amigável e motivadora para o início do dia.
- Formatação: Apresente os dados em tópicos curtos e organizados com marcadores (bullet points) e emojis elegantes.
- Tarefas a contemplar:
  * Agenda: Liste os compromissos em ordem cronológica (se não houver, mencione de forma leve e produtiva).
  * E-mails: Destaque mensagens prioritárias que exigem atenção.
  * Clima: Destaque máxima/mínima e recomendação prática (ex: levar guarda-chuva se houver chuva).
  * Cotação de Moedas: Informe o Dólar comercial de forma rápida.
  * Notícias: Faça um resumo ultra-rápido de 1 a 2 manchetes mais relevantes do dia.
- Clareza: Seja direto ao ponto para leitura rápida em tela de smartphone ou notificação.
- Não invente dados fora do fornecido. Seja objetivo e profissional.
"""

        # Se houver chave Gemini válida, faz a chamada à API
        if api_key and api_key.strip():
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key.strip())
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"Erro na chamada do Gemini: {e}")

        # Geração de fallback estruturada e elegante (caso a chave ainda não tenha sido inserida)
        rain_note = "Leve um guarda-chuva ao sair." if weather['rain_prob'] >= 40 else "Tempo favorável para atividades ao ar livre."
        
        agenda_block = "\n".join([f"  * **{timezone.localtime(ev.start_time).strftime('%H:%M')}** - {ev.title} {'⚠️' if ev.is_important else ''}" for ev in agenda_events]) if agenda_events else "  * Nenhum compromisso urgente agendado para hoje. Aproveite para focar em tarefas prioritárias!"
        
        email_block = "\n".join([f"  * **{em.sender}**: {em.subject} - {em.snippet[:80]}..." for em in email_highlights]) if email_highlights else "  * Caixa de entrada em dia, sem e-mails críticos pendentes."

        news_block = "\n".join([f"  * **{n.get('source', 'Notícia')}**: {n.get('title')}" for n in (news_items or [])[:3]]) if news_items else "  * Notícias do momento em atualização."

        fallback_briefing = f"""Olá, Rhaony! Aqui é a Bella, sua assistente pessoal! Preparei com muito carinho o seu resumo essencial para hoje:

* **📅 Agenda de Hoje:**
{agenda_block}

* **✉️ E-mails em Destaque:**
{email_block}

* **⛅ Previsão do Tempo ({weather['city']}):**
  * Temperatura: Mínima de **{weather['temp_min']}°C** e Máxima de **{weather['temp_max']}°C** (Atual: {weather['current_temp']}°C).
  * Condição: {weather['condition']}. Chance de chuva em {weather['rain_prob']}%. {rain_note}

* **💵 Cotação do Dólar Comercial (USD/BRL):**
  * Compra: **R$ {currency['bid']}** | Venda: **R$ {currency['ask']}**
  * Variação recente: {currency['variation']}

* **📰 Principais Notícias do Dia:**
{news_block}

*Tenha um ótimo e produtivo dia!*
"""
        return fallback_briefing��� Cotação do Dólar Comercial (USD/BRL):**
  * Compra: **R$ {currency['bid']}** | Venda: **R$ {currency['ask']}**
  * Variação recente: {currency['variation']}

*Tenha um ótimo dia!*
"""
        return fallback_briefing


class BriefingOrchestrator:
    @staticmethod
    def get_today_briefing(force_refresh=False):
        """Orquestra a coleta de dados, consulta ao Gemini e montagem do payload do app"""
        today = timezone.localdate()
        
        # Verifica preferências do usuário
        pref = UserPreference.objects.first()
        city = pref.city_name if pref else settings.DEFAULT_CITY
        lat = float(pref.latitude) if pref else settings.DEFAULT_LAT
        lon = float(pref.longitude) if pref else settings.DEFAULT_LON
        api_key = pref.gemini_api_key if pref and pref.gemini_api_key else None
        
        # Agenda de hoje (ordem cronológica)
        start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        events = list(CalendarEvent.objects.filter(start_time__gte=start_of_day, start_time__lte=end_of_day).order_by('start_time'))
        
        # E-mails importantes
        emails = list(EmailHighlight.objects.filter(is_read=False).order_by('-is_important', '-received_at')[:5])
        
        # Obtém Clima e Dólar
        weather = WeatherService.get_weather(lat=lat, lon=lon, city=city)
        currency = CurrencyService.get_usd_rate()
        
        # Verifica se já existe um briefing salvo para hoje sem necessidade de forçar
        latest_briefing = DailyBriefing.objects.filter(date=today).first()
        
        if not latest_briefing or force_refresh:
            summary_text = GeminiService.generate_briefing(weather, currency, events, emails, custom_api_key=api_key)
            if latest_briefing:
                latest_briefing.weather_city = city
                latest_briefing.weather_temp_min = weather['temp_min']
                latest_briefing.weather_temp_max = weather['temp_max']
                latest_briefing.weather_condition = weather['condition']
                latest_briefing.usd_bid = currency['bid']
                latest_briefing.usd_ask = currency['ask']
                latest_briefing.usd_variation = currency['variation']
                latest_briefing.gemini_summary = summary_text
                latest_briefing.agenda_count = len(events)
                latest_briefing.email_count = len(emails)
                latest_briefing.save()
            else:
                latest_briefing = DailyBriefing.objects.create(
                    date=today,
                    weather_city=city,
                    weather_temp_min=weather['temp_min'],
                    weather_temp_max=weather['temp_max'],
                    weather_condition=weather['condition'],
                    usd_bid=currency['bid'],
                    usd_ask=currency['ask'],
                    usd_variation=currency['variation'],
                    gemini_summary=summary_text,
                    agenda_count=len(events),
                    email_count=len(emails)
                )
            
        return {
            "id": latest_briefing.id,
            "date": latest_briefing.date.strftime("%d/%m/%Y"),
            "date_iso": latest_briefing.date.isoformat(),
            "weather": weather,
            "currency": currency,
            "summary": latest_briefing.gemini_summary,
            "events": [
                {
                    "id": ev.id,
                    "title": ev.title,
                    "description": ev.description,
                    "start_time": timezone.localtime(ev.start_time).strftime("%H:%M"),
                    "category": ev.category,
                    "category_label": ev.get_category_display(),
                    "is_important": ev.is_important
                } for ev in events
            ],
            "emails": [
                {
                    "id": em.id,
                    "sender": em.sender,
                    "sender_email": em.sender_email,
                    "subject": em.subject,
                    "snippet": em.snippet,
                    "received_at": timezone.localtime(em.received_at).strftime("%H:%M"),
                    "is_important": em.is_important,
                    "action_required": em.action_required
                } for em in emails
            ]
        }


class ChatAssistantService:
    """Serviço de conversação interativa por voz e texto com o Google Gemini e execução de ações"""

    @staticmethod
    def process_message(user_text, api_key_override=None):
        import re
        import json

        pref = UserPreference.objects.first()
        city = pref.city_name if pref else settings.DEFAULT_CITY
        lat = float(pref.latitude) if pref else settings.DEFAULT_LAT
        lon = float(pref.longitude) if pref else settings.DEFAULT_LON
        api_key = api_key_override or (pref.gemini_api_key if pref and pref.gemini_api_key else None) or getattr(settings, "GEMINI_API_KEY", "")

        # Memória Conversacional Contínua: busca as mensagens recentes anteriores
        recent_history = list(ChatMessage.objects.order_by('-created_at')[:8])
        recent_history.reverse()
        history_lines = []
        for msg in recent_history:
            sender = "Usuário" if msg.role == 'user' else "Bella"
            history_lines.append(f"- {sender}: {msg.content}")
        history_str = "\n".join(history_lines) if history_lines else "Início da conversa, sem histórico anterior."

        # Registra mensagem do usuário no banco
        user_msg = ChatMessage.objects.create(role='user', content=user_text)

        # Contexto atualizado em tempo real
        now = timezone.localtime()
        weather = WeatherService.get_weather(lat=lat, lon=lon, city=city)
        currency = CurrencyService.get_usd_rate()
        
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        events = list(CalendarEvent.objects.filter(start_time__gte=today_start).order_by('start_time')[:10])
        emails = list(EmailHighlight.objects.filter(is_read=False).order_by('-received_at')[:5])

        events_str = "\n".join([f"- ID {ev.id}: {timezone.localtime(ev.start_time).strftime('%d/%m %H:%M')} - {ev.title} ({ev.get_category_display()})" for ev in events]) or "Nenhum compromisso agendado."
        emails_str = "\n".join([f"- De {em.sender}: {em.subject} ({em.snippet[:60]}...)" for em in emails]) or "Nenhum e-mail não lido."

        # Prompt com capacidade de chamada de ações (Action Calling) e Memória Contínua
        system_instruction = f"""Você é a Bella, uma assistente pessoal inteligente, jovem, carismática, alegre, empática e prestativa. Você fala de forma natural, moderna, doce e agradável, em português brasileiro. Seu tom é o de uma moça jovem, profissional e atenciosa.
Data/Hora atual no Brasil: {now.strftime('%d/%m/%Y %H:%M:%S (%A)')}.
Cidade do usuário: {city}.
Clima atual: {weather['condition']}, {weather['current_temp']}°C (Mín: {weather['temp_min']}°C, Máx: {weather['temp_max']}°C, Chuva: {weather['rain_prob']}%).
Cotação Dólar (USD/BRL): Compra R$ {currency['bid']}, Venda R$ {currency['ask']}, Variação: {currency['variation']}.

Compromissos agendados:
{events_str}

E-mails recentes:
{emails_str}

HISTÓRICO RECENTE DA CONVERSA (MEMÓRIA CONTEXTUAL):
{history_str}

INSTRUÇÃO DE CONTINUIDADE E MEMÓRIA:
Você tem memória contínua das mensagens acima. Se o usuário fizer referência a algo dito anteriormente (por exemplo "ele", "ela", "aquilo", "o que você disse antes", "e amanhã?", "mude o horário para as 16h"), interprete a intenção conectando com o histórico anterior e responda de forma natural e precisa, sem reiniciar a conversa do zero.

SUAS CAPACIDADES DE AÇÃO:
Você pode executar ações para o usuário respondendo no formato JSON rígido quando o usuário solicitar adicionar ou consultar algo.
Possíveis ações:
1. "ADD_EVENT": Quando o usuário pedir para agendar/marcar compromisso ou reunião.
   action_data: {{"title": "Título", "time": "HH:MM", "date_offset_days": 0, "category": "work|personal|health|study|other", "is_important": true/false}}
   (date_offset_days: 0 para hoje, 1 para amanhã).
2. "ADD_TASK": Quando o usuário pedir para criar, adicionar ou anotar uma tarefa ou afazer.
   action_data: {{"title": "Título da Tarefa", "priority": "high|medium|low", "category": "work|personal|health|study|other"}}
3. "ADD_EMAIL": Quando o usuário pedir para registrar um e-mail ou aviso importante.
   action_data: {{"sender": "Nome", "subject": "Assunto", "snippet": "Trecho/Anotação", "is_important": true}}
4. "NONE": Para respostas normais de conversa, conselhos, dúvidas de clima, cotação ou bate-papo.

FORMATO OBRIGATÓRIO DE RESPOSTA JSON:
{{
  "action": "ADD_EVENT" | "ADD_TASK" | "ADD_EMAIL" | "NONE",
  "action_data": {{ ... }} ou null,
  "reply": "Sua resposta simpática, clara e em português para ser lida por voz no celular."
}}
Responda EXCLUSIVAMENTE o objeto JSON válido, sem crases extras ou markdown envolvente."""

        reply_text = ""
        action_type = "NONE"
        action_details = {}

        # 1. Tentativa via Google Gemini AI
        if api_key and api_key.strip():
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key.strip())
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content([system_instruction, f"Usuário: {user_text}"])
                raw_txt = response.text.strip()
                
                # Limpa crases de json se houver
                if raw_txt.startswith("```json"):
                    raw_txt = raw_txt[7:]
                if raw_txt.startswith("```"):
                    raw_txt = raw_txt[3:]
                if raw_txt.endswith("```"):
                    raw_txt = raw_txt[:-3]
                raw_txt = raw_txt.strip()

                parsed = json.loads(raw_txt)
                action_type = parsed.get("action", "NONE")
                action_details = parsed.get("action_data") or {}
                reply_text = parsed.get("reply", "")
            except Exception as e:
                print(f"Erro no processamento do Gemini Chat: {e}")

        # 2. Fallback Inteligente baseado em Regras & PNL (se não houver chave ou falha)
        if not reply_text:
            lower = user_text.lower()
            
            # Reconhecimento de intenção de agendamento (ex: "adicione reunião às 15h")
            if any(k in lower for k in ["adicione", "adicionar", "agende", "agendar", "marque", "marcar", "lembre-me"]):
                # Tenta capturar horário (ex: "15h", "15:30", "15h30", "as 14")
                time_match = re.search(r'(?:às|as|à|a)?\s*(\d{1,2})(?:[:h](\d{2})|h)?', lower)
                hour = 9
                minute = 0
                if time_match:
                    h_val = time_match.group(1)
                    m_val = time_match.group(2)
                    if h_val:
                        hour = min(max(int(h_val), 0), 23)
                    if m_val:
                        minute = min(max(int(m_val), 0), 59)
                
                # Título limpo
                clean_title = re.sub(r'^(?:por favor,?\s*)?(?:adicione|agende|marque|coloque na agenda)\s*', '', user_text, flags=re.IGNORECASE)
                clean_title = clean_title.strip() or "Novo compromisso"

                action_type = "ADD_EVENT"
                action_details = {
                    "title": clean_title,
                    "time": f"{hour:02d}:{minute:02d}",
                    "date_offset_days": 1 if "amanhã" in lower else 0,
                    "category": "health" if any(w in lower for w in ["treino", "academia", "médico", "dentista", "caminhada"]) else "work",
                    "is_important": any(w in lower for w in ["urgente", "importante", "prioridade"])
                }
                day_label = "amanhã" if action_details["date_offset_days"] == 1 else "hoje"
                reply_text = f"Prontinho! Já anotei '{clean_title}' na sua agenda para {day_label} às {hour:02d}:{minute:02d}!"
            
            elif any(k in lower for k in ["clima", "tempo", "chov", "temperatura", "chuva", "calor", "frio"]):
                reply_text = f"Em {city}, a previsão para hoje é de tempo {weather['condition'].lower()}, com temperatura atual de {weather['current_temp']}°C. A máxima chega a {weather['temp_max']}°C e a chance de chuva é de {weather['rain_prob']}%."
            
            elif any(k in lower for k in ["dólar", "dolar", "cotação", "cotacao", "câmbio", "cambio"]):
                reply_text = f"O Dólar comercial está cotado a R$ {currency['bid']} para compra e R$ {currency['ask']} para venda, com variação de {currency['variation']}."
            
            elif any(k in lower for k in ["tarefa", "afazer", "anote", "lembrete"]):
                clean_title = re.sub(r'^(?:por favor,?\s*)?(?:adicione|adicionar|crie|criar|coloque|anote)\s*(?:uma\s*)?(?:tarefa|afazer|lembrete)?\s*(?:de|para)?\s*', '', user_text, flags=re.IGNORECASE).strip() or "Nova tarefa"
                prio = "high" if any(w in lower for w in ["urgente", "alta", "prioridade"]) else "medium"
                action_type = "ADD_TASK"
                action_details = {
                    "title": clean_title,
                    "priority": prio,
                    "category": "personal" if any(w in lower for w in ["casa", "mercado", "comprar", "pessoal"]) else "work"
                }
                reply_text = f"Com certeza! Já criei a tarefa '{clean_title}' na sua lista de afazeres!"

            elif any(k in lower for k in ["agenda", "compromisso", "o que tenho", "reunião"]):
                if events:
                    ev_items = ", ".join([f"{timezone.localtime(e.start_time).strftime('%H:%M')} - {e.title}" for e in events[:3]])
                    reply_text = f"Seus próximos compromissos são: {ev_items}."
                else:
                    reply_text = "Você está com o dia totalmente livre, sem nenhum compromisso agendado!"
            
            else:
                reply_text = f"Oi! Eu sou a Bella, sua assistente pessoal! Posso agendar seus compromissos, ver o clima para {city}, acompanhar moedas ou anotar tarefas para você. Como posso te ajudar agora?"

        # 3. Execução da Ação no Banco de Dados
        executed_action_log = None
        if action_type == "ADD_EVENT" and action_details:
            try:
                days_offset = int(action_details.get("date_offset_days", 0))
                target_date = now.date() + datetime.timedelta(days=days_offset)
                time_str = action_details.get("time", "09:00")
                if ":" in time_str:
                    h, m = map(int, time_str.split(":")[:2])
                else:
                    h, m = 9, 0
                
                target_dt = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time(h, m)))
                
                new_event = CalendarEvent.objects.create(
                    title=action_details.get("title", "Novo Compromisso"),
                    start_time=target_dt,
                    category=action_details.get("category", "work"),
                    is_important=bool(action_details.get("is_important", False))
                )
                executed_action_log = {
                    "type": "event_created",
                    "event_id": new_event.id,
                    "title": new_event.title,
                    "time": timezone.localtime(new_event.start_time).strftime("%H:%M")
                }
            except Exception as err:
                print(f"Erro ao salvar evento criado pelo chat: {err}")

        elif action_type == "ADD_EMAIL" and action_details:
            try:
                new_email = EmailHighlight.objects.create(
                    sender=action_details.get("sender", "Remetente"),
                    subject=action_details.get("subject", "Assunto"),
                    snippet=action_details.get("snippet", ""),
                    is_important=bool(action_details.get("is_important", True)),
                    received_at=now
                )
                executed_action_log = {
                    "type": "email_created",
                    "email_id": new_email.id,
                    "subject": new_email.subject
                }
            except Exception as err:
                print(f"Erro ao salvar e-mail criado pelo chat: {err}")

        elif action_type == "ADD_TASK" and action_details:
            try:
                new_task = QuickTask.objects.create(
                    title=action_details.get("title", "Nova Tarefa"),
                    priority=action_details.get("priority", "medium"),
                    category=action_details.get("category", "work"),
                    due_date=now.date()
                )
                executed_action_log = {
                    "type": "task_created",
                    "task_id": new_task.id,
                    "title": new_task.title,
                    "priority": new_task.priority
                }
            except Exception as err:
                print(f"Erro ao salvar tarefa criada pelo chat: {err}")

        # Salva resposta do assistente
        assistant_msg = ChatMessage.objects.create(
            role='assistant',
            content=reply_text,
            action_type=action_type,
            action_details=json.dumps(executed_action_log or action_details)
        )

        return {
            "reply": reply_text,
            "action_type": action_type,
            "action_executed": executed_action_log,
            "message_id": assistant_msg.id,
            "created_at": assistant_msg.created_at.strftime("%H:%M")
        }


class NotificationService:
    """Serviço de envio do resumo diário para Telegram e WhatsApp"""

    @staticmethod
    def send_telegram_message(bot_token, chat_id, text):
        """Envia mensagem de texto via Telegram Bot API"""
        if not bot_token or not chat_id:
            return {"success": False, "error": "Token do Bot ou Chat ID não configurados."}

        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        
        # Limite de tamanho de mensagem do Telegram é 4096 caracteres
        truncated_text = text[:4000] if len(text) > 4000 else text

        try:
            # Tenta envio com formatação Markdown
            payload = {
                "chat_id": chat_id.strip(),
                "text": truncated_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            res = requests.post(url, json=payload, timeout=8)
            res_json = res.json()

            if res_json.get("ok"):
                return {"success": True, "message_id": res_json.get("result", {}).get("message_id")}
            
            # Se falhar por erro de parsing de Markdown, tenta em texto simples
            payload.pop("parse_mode", None)
            res_retry = requests.post(url, json=payload, timeout=8)
            retry_json = res_retry.json()
            if retry_json.get("ok"):
                return {"success": True, "message_id": retry_json.get("result", {}).get("message_id")}
            else:
                return {"success": False, "error": retry_json.get("description", "Falha no envio Telegram")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_daily_briefing_telegram(force_refresh=False):
        """Coleta o briefing de hoje e envia para o Telegram configurado"""
        pref = UserPreference.objects.first()
        bot_token = (pref.telegram_bot_token if pref and pref.telegram_bot_token else None) or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = (pref.telegram_chat_id if pref and pref.telegram_chat_id else None) or os.getenv("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            return {"success": False, "error": "Configure o Token do Bot e o Chat ID nas configurações do app."}

        briefing_data = BriefingOrchestrator.get_today_briefing(force_refresh=force_refresh)
        text = briefing_data.get("summary", "")

        header = f"📱 *SEU RESUMO DIÁRIO - {briefing_data.get('date')}*\n"
        full_msg = f"{header}\n{text}\n\n_Enviado pelo seu Assistente Pessoal PWA_"

        return NotificationService.send_telegram_message(bot_token, chat_id, full_msg)

    @staticmethod
    def test_telegram_connection(bot_token, chat_id):
        """Envia mensagem de teste de conexão para o Telegram"""
        now = timezone.localtime().strftime("%d/%m/%Y às %H:%M:%S")
        msg = f"🔔 *Teste de Conexão Bem-Sucedido!*\n\nSeu Assistente Pessoal PWA está conectado com este chat do Telegram.\nData/Hora: {now}."
        return NotificationService.send_telegram_message(bot_token, chat_id, msg)

    @staticmethod
    def format_whatsapp_share_text(briefing_data):
        """Formata o texto do briefing com sintaxe nativa do WhatsApp (*negrito*, emojis)"""
        text = briefing_data.get("summary", "")
        # O WhatsApp já suporta *negrito* nativamente
        date_str = briefing_data.get("date", "")
        wa_text = f"📱 *RESUMO DO DIA ({date_str})*\n\n{text}\n\n_Enviado via Assistente Pessoal_"
        return wa_text


class NeuralVoiceService:
    """Serviço de Síntese Vocal Neural Ultra-Realista em Português Brasileiro (Microsoft Edge-TTS)"""
    DEFAULT_VOICE = "pt-BR-ThalitaMultilingualNeural"
    VOICES = {
        "thalita": "pt-BR-ThalitaMultilingualNeural",   # Jovem, moderna, alegre, expressiva
        "francisca": "pt-BR-FranciscaNeural",            # Doce, acolhedora, calma
        "antonio": "pt-BR-AntonioNeural",                # Masculino profissional
    }

    @staticmethod
    def clean_text_for_speech(text: str) -> str:
        """Limpa caracteres de markdown, símbolos, formatações e abreviações para dicção 100% fluida e humana"""
        if not text:
            return ""
        import re
        t = text
        # Remove blocos de código
        t = re.sub(r'```[\s\S]*?```', '', t)
        t = re.sub(r'`([^`]+)`', r'\1', t)
        # Remove links markdown [texto](url) -> texto
        t = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
        # Remove asteriscos, hashtags e sublinhados
        t = re.sub(r'\*{1,3}', '', t)
        t = re.sub(r'#{1,6}\s*', '', t)
        t = re.sub(r'_{1,3}', '', t)
        # Expande símbolos e moedas para fala fluida
        t = t.replace('R$', 'reais ')
        t = t.replace('US$', 'dólares ')
        t = t.replace('USD', 'dólares')
        t = t.replace('EUR', 'euros')
        t = t.replace('BTC', 'Bitcoin')
        t = t.replace('°C', ' graus ')
        t = t.replace('%', ' por cento')
        t = t.replace('•', ', ')
        # Remove emojis para evitar que o sintetizador tente ler o nome do emoji
        t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
        # Normaliza pontuação e quebras de linha
        t = re.sub(r'\n+', '. ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    @classmethod
    async def _async_synthesize(cls, text: str, voice_code: str = "thalita", rate: str = "+0%", pitch: str = "+0Hz") -> bytes:
        import edge_tts
        clean_text = cls.clean_text_for_speech(text)
        if not clean_text:
            clean_text = "Tudo certo por aqui."

        voice = cls.VOICES.get(voice_code, voice_code)
        if not voice or not voice.startswith("pt-BR"):
            voice = cls.DEFAULT_VOICE

        communicate = edge_tts.Communicate(clean_text, voice, rate=rate, pitch=pitch)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    @classmethod
    def synthesize_to_mp3(cls, text: str, voice_code: str = "thalita", rate: str = "+0%", pitch: str = "+0Hz") -> bytes:
        """Gera áudio MP3 sincronamente, compatível com views Django normais"""
        import asyncio
        try:
            return asyncio.run(cls._async_synthesize(text, voice_code=voice_code, rate=rate, pitch=pitch))
        except RuntimeError:
            # Se a thread atual já possuir event loop ativo
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(cls._async_synthesize(text, voice_code=voice_code, rate=rate, pitch=pitch))
            finally:
                loop.close()



