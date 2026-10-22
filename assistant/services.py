import os
import requests
import datetime
from django.utils import timezone
from django.conf import settings
from .models import CalendarEvent, EmailHighlight, DailyBriefing, UserPreference, ChatMessage, QuickTask, VoiceMemo

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
             "weekday": ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"][(today.weekday() + i) % 7],
             "temp_max": 26.0, "temp_min": 18.0, "rain_prob": 40, "icon": "⛅"}
            for i in range(7)
        ]



class WebSearchService:
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
    """Serviço de conversação interativa por voz e texto com Google Gemini Function Calling e execução de ferramentas"""

    @staticmethod
    def parse_date_string(date_str: str, base_date: datetime.date = None) -> datetime.date:
        """Interpreta termos temporais em português ou formatos de data"""
        import re
        if not base_date:
            base_date = timezone.localdate()
        if not date_str:
            return base_date
        
        clean = str(date_str).lower().strip()
        if "hoje" in clean:
            return base_date
        if "amanhã" in clean or "amanha" in clean:
            return base_date + datetime.timedelta(days=1)
        if "depois de amanhã" in clean or "depois de amanha" in clean:
            return base_date + datetime.timedelta(days=2)
        
        weekdays = {
            "segunda": 0, "segunda-feira": 0,
            "terça": 1, "terca": 1, "terça-feira": 1,
            "quarta": 2, "quarta-feira": 2,
            "quinta": 3, "quinta-feira": 3,
            "sexta": 4, "sexta-feira": 4,
            "sábado": 5, "sabado": 5,
            "domingo": 6
        }
        for name, wday in weekdays.items():
            if name in clean:
                days_ahead = (wday - base_date.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return base_date + datetime.timedelta(days=days_ahead)
                
        # Padrão YYYY-MM-DD
        match_iso = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', clean)
        if match_iso:
            y, m, d = map(int, match_iso.groups())
            return datetime.date(y, m, d)
            
        # Padrão DD/MM/YYYY ou DD/MM
        match_br = re.search(r'(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?', clean)
        if match_br:
            d = int(match_br.group(1))
            m = int(match_br.group(2))
            y = int(match_br.group(3)) if match_br.group(3) else base_date.year
            if y < 100:
                y += 2000
            return datetime.date(y, m, d)
            
        return base_date

    @staticmethod
    def parse_time_string(time_str: str) -> tuple:
        """Extrai horas e minutos de expressões textuais como '15:30', '16h', '16h45', 'às 9'"""
        import re
        if not time_str:
            return (9, 0)
        clean = str(time_str).lower().strip()
        match = re.search(r'(?:às|as|à|a)?\s*(\d{1,2})(?:[:h](\d{2})|h)?', clean)
        if match:
            h = int(match.group(1))
            m = int(match.group(2)) if match.group(2) else 0
            h = max(0, min(h, 23))
            m = max(0, min(m, 59))
            return (h, m)
        return (9, 0)

    @staticmethod
    def process_message(user_text, api_key_override=None):
        import re
        import json

        pref = UserPreference.objects.first()
        city = pref.city_name if pref else settings.DEFAULT_CITY
        lat = float(pref.latitude) if pref else settings.DEFAULT_LAT
        lon = float(pref.longitude) if pref else settings.DEFAULT_LON
        api_key = api_key_override or (pref.gemini_api_key if pref and pref.gemini_api_key else None) or getattr(settings, "GEMINI_API_KEY", "")

        now = timezone.localtime()
        weather = WeatherService.get_weather(lat=lat, lon=lon, city=city)
        currency = CurrencyService.get_usd_rate()

        # Registra a mensagem do usuário no banco
        user_msg = ChatMessage.objects.create(role='user', content=user_text)

        executed_actions = []

        # =========================================================================
        # DEFINIÇÃO DE FERRAMENTAS (TOOLS / FUNCTION CALLING DO GEMINI)
        # =========================================================================
        def search_web_tool(query: str) -> str:
            """Pesquisa na web e no Google Notícias em tempo real para obter informações atualizadas sobre fatos recentes, notícias de hoje, resultados de jogos, lançamentos ou cotações."""
            results = WebSearchService.search_web(query, max_results=3)
            executed_actions.append({"type": "web_search", "query": query})
            if not results:
                return f"Nenhum resultado recente encontrado na web para '{query}'."
            formatted = []
            for r in results:
                formatted.append(f"Título: {r.get('title')}\nResumo: {r.get('snippet')}\nLink: {r.get('url')}")
            return "\n---\n".join(formatted)

        def add_calendar_event_tool(title: str, date_str: str = "hoje", time_str: str = "09:00", category: str = "work", is_important: bool = False, location: str = "") -> str:
            """Agenda um novo compromisso ou reunião no calendário. date_str pode ser 'hoje', 'amanhã', dia da semana ou YYYY-MM-DD. time_str no formato 'HH:MM'."""
            d = ChatAssistantService.parse_date_string(date_str, now.date())
            h, m = ChatAssistantService.parse_time_string(time_str)
            target_dt = timezone.make_aware(datetime.datetime.combine(d, datetime.time(h, m)))
            ev = CalendarEvent.objects.create(
                title=title.strip(),
                start_time=target_dt,
                category=category if category in ['work', 'personal', 'health', 'study', 'other'] else 'work',
                is_important=bool(is_important),
                location=location or ""
            )
            time_formatted = timezone.localtime(ev.start_time).strftime("%H:%M")
            executed_actions.append({
                "type": "event_created",
                "event_id": ev.id,
                "title": ev.title,
                "time": time_formatted,
                "date": d.strftime("%d/%m")
            })
            return f"Compromisso '{ev.title}' agendado com sucesso para {d.strftime('%d/%m/%Y')} às {time_formatted}."

        def edit_calendar_event_tool(search_term: str, new_time: str = None, new_date_str: str = None, new_title: str = None) -> str:
            """Edita ou remarca um compromisso existente no calendário. Localiza pelo nome (search_term) e atualiza o horário (new_time ex: '16:00'), nova data (new_date_str ex: 'amanhã') ou título (new_title)."""
            ev = CalendarEvent.objects.filter(title__icontains=search_term).order_by('-start_time').first()
            if not ev:
                return f"Não encontrei nenhum compromisso na agenda contendo '{search_term}'."

            current_dt = timezone.localtime(ev.start_time)
            target_date = current_dt.date()
            target_time = (current_dt.hour, current_dt.minute)

            if new_date_str:
                target_date = ChatAssistantService.parse_date_string(new_date_str, now.date())
            if new_time:
                target_time = ChatAssistantService.parse_time_string(new_time)

            ev.start_time = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time(*target_time)))
            if new_title:
                ev.title = new_title.strip()
            ev.save()

            formatted_dt = timezone.localtime(ev.start_time).strftime("%d/%m/%Y às %H:%M")
            executed_actions.append({
                "type": "event_updated",
                "event_id": ev.id,
                "title": ev.title,
                "new_time": timezone.localtime(ev.start_time).strftime("%H:%M"),
                "new_date": target_date.strftime("%d/%m")
            })
            return f"Compromisso '{ev.title}' remarcado para {formatted_dt} com sucesso!"

        def delete_calendar_event_tool(search_term: str) -> str:
            """Exclui ou cancela um compromisso da agenda localizado pelo nome ou palavra-chave."""
            ev = CalendarEvent.objects.filter(title__icontains=search_term).order_by('-start_time').first()
            if not ev:
                return f"Não encontrei nenhum compromisso contendo '{search_term}' para excluir."
            title = ev.title
            ev.delete()
            executed_actions.append({
                "type": "event_deleted",
                "title": title
            })
            return f"Compromisso '{title}' excluído da sua agenda."

        def add_task_tool(title: str, priority: str = "medium", category: str = "work", due_date_str: str = "hoje") -> str:
            """Cria uma nova tarefa ou afazer na lista de afazeres. priority pode ser 'low', 'medium' ou 'high'."""
            d = ChatAssistantService.parse_date_string(due_date_str, now.date())
            task = QuickTask.objects.create(
                title=title.strip(),
                priority=priority if priority in ['low', 'medium', 'high'] else 'medium',
                category=category if category in ['work', 'personal', 'health', 'study', 'other'] else 'work',
                due_date=d
            )
            executed_actions.append({
                "type": "task_created",
                "task_id": task.id,
                "title": task.title,
                "priority": task.priority
            })
            return f"Tarefa '{task.title}' criada com sucesso na lista de afazeres!"

        def complete_task_tool(search_term: str) -> str:
            """Marca uma tarefa existente como concluída ou finalizada na lista de afazeres, localizando-a pelo nome (search_term)."""
            task = QuickTask.objects.filter(is_done=False, title__icontains=search_term).first()
            if not task:
                already_done = QuickTask.objects.filter(is_done=True, title__icontains=search_term).first()
                if already_done:
                    return f"A tarefa '{already_done.title}' já estava marcada como concluída."
                return f"Não encontrei nenhuma tarefa pendente com o termo '{search_term}'."

            task.is_done = True
            task.completed_at = timezone.now()
            task.save()
            executed_actions.append({
                "type": "task_completed",
                "task_id": task.id,
                "title": task.title
            })
            return f"Tarefa '{task.title}' marcada como concluída com sucesso! Parabéns!"

        def delete_task_tool(search_term: str) -> str:
            """Exclui ou remove uma tarefa da lista de afazeres pelo nome ou palavra-chave."""
            task = QuickTask.objects.filter(title__icontains=search_term).first()
            if not task:
                return f"Não encontrei nenhuma tarefa contendo '{search_term}' para excluir."
            title = task.title
            task.delete()
            executed_actions.append({
                "type": "task_deleted",
                "title": title
            })
            return f"Tarefa '{title}' removida da sua lista de afazeres."

        def list_agenda_or_tasks_tool(item_type: str = "all", date_str: str = "hoje") -> str:
            """Consulta e lista compromissos da agenda e/ou tarefas pendentes para hoje ou uma data específica (item_type: 'events', 'tasks' ou 'all')."""
            d = ChatAssistantService.parse_date_string(date_str, now.date())
            start_dt = timezone.make_aware(datetime.datetime.combine(d, datetime.time(0, 0, 0)))
            end_dt = timezone.make_aware(datetime.datetime.combine(d, datetime.time(23, 59, 59)))

            report = []
            if item_type in ["events", "all"]:
                events = list(CalendarEvent.objects.filter(start_time__gte=start_dt, start_time__lte=end_dt).order_by('start_time'))
                if events:
                    ev_list = [f"- {timezone.localtime(e.start_time).strftime('%H:%M')} - {e.title} ({e.get_category_display()})" for e in events]
                    report.append(f"Compromissos para {d.strftime('%d/%m/%Y')}:\n" + "\n".join(ev_list))
                else:
                    report.append(f"Nenhum compromisso agendado para {d.strftime('%d/%m/%Y')}.")

            if item_type in ["tasks", "all"]:
                tasks = list(QuickTask.objects.filter(is_done=False).order_by('-priority', 'created_at')[:8])
                if tasks:
                    t_list = [f"- {t.title} (Prioridade: {t.get_priority_display()})" for t in tasks]
                    report.append("Tarefas pendentes:\n" + "\n".join(t_list))
                else:
                    report.append("Nenhuma tarefa pendente na lista.")

            return "\n\n".join(report)

        tools_list = [
            search_web_tool,
            add_calendar_event_tool,
            edit_calendar_event_tool,
            delete_calendar_event_tool,
            add_task_tool,
            complete_task_tool,
            delete_task_tool,
            list_agenda_or_tasks_tool,
        ]

        # Contexto do sistema para o Gemini
        system_instruction = f"""Você é a Bella, uma assistente pessoal inteligente, jovem, carismática, alegre, empática e prestativa. Você fala de forma natural, moderna, doce e agradável, em português brasileiro.
Data/Hora atual no Brasil: {now.strftime('%d/%m/%Y %H:%M:%S (%A)')}.
Cidade do usuário: {city}.
Clima atual: {weather['condition']}, {weather['current_temp']}°C (Mín: {weather['temp_min']}°C, Máx: {weather['temp_max']}°C, Chuva: {weather['rain_prob']}%).
Cotação Dólar (USD/BRL): Compra R$ {currency['bid']}, Venda R$ {currency['ask']}, Variação: {currency['variation']}.

SUAS FERRAMENTAS E REGRAS:
1. PESQUISA NA WEB: Sempre que o usuário perguntar sobre fatos recentes, notícias de hoje, resultados de jogos de futebol, tecnologia, filmes, eventos ou informações em tempo real, use a ferramenta 'search_web_tool'.
2. TAREFAS:
   - Para criar tarefa: use 'add_task_tool'.
   - Para concluir/marcar como feita: use 'complete_task_tool'.
   - Para excluir: use 'delete_task_tool'.
3. AGENDA / COMPROMISSOS:
   - Para agendar: use 'add_calendar_event_tool'.
   - Para remarcar ou mudar horário/data: use 'edit_calendar_event_tool'.
   - Para cancelar/excluir: use 'delete_calendar_event_tool'.
   - Para consultar o que tem para fazer: use 'list_agenda_or_tasks_tool'.
4. TOM DE RESPOSTA: Seja sempre acolhedora, clara e objetiva. Responda diretamente ao usuário em português brasileiro fluido para ser ouvido por voz."""

        reply_text = ""

        # 1. Tentativa via Google Gemini AI com Function Calling Oficial
        if api_key and api_key.strip():
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key.strip())
                model = genai.GenerativeModel(
                    "gemini-1.5-flash",
                    system_instruction=system_instruction,
                    tools=tools_list
                )

                # Constrói histórico recente alternando user/model
                recent_messages = list(ChatMessage.objects.order_by('-created_at')[:8])
                recent_messages.reverse()
                # Remove a última mensagem que acabamos de criar para não duplicar no send_message
                if recent_messages and recent_messages[-1].id == user_msg.id:
                    recent_messages.pop()

                formatted_history = []
                expected_role = "user"
                for m in recent_messages:
                    role = "user" if m.role == "user" else "model"
                    if role == expected_role and m.content and m.content.strip():
                        formatted_history.append({
                            "role": role,
                            "parts": [m.content.strip()]
                        })
                        expected_role = "model" if expected_role == "user" else "user"

                # Histórico no Gemini deve terminar com 'model' para o próximo 'send_message' ser 'user'
                if formatted_history and formatted_history[-1]["role"] == "user":
                    formatted_history.pop()

                chat = model.start_chat(history=formatted_history, enable_automatic_function_calling=True)
                response = chat.send_message(user_text)
                if response and response.text:
                    reply_text = response.text.strip()
            except Exception as e:
                print(f"Erro no Gemini Function Calling: {e}")

        # 2. Fallback Inteligente Avançado com PNL e Ferramentas Locais (caso sem chave ou instabilidade)
        if not reply_text:
            lower = user_text.lower()

            # A. Pesquisa na Web (Ex: "quem ganhou o jogo", "últimas notícias", "pesquise na web", "resultado de")
            if any(k in lower for k in ["quem ganhou", "resultado do", "resultado de", "lançamento", "pesquise", "procure na web", "procure na internet", "notícias sobre", "noticias sobre", "notícia sobre"]):
                clean_query = re.sub(r'^(?:por favor,?\s*)?(?:bella,?\s*)?(?:pesquise|procure|busque|veja|me diga|qual o|quem)\s*(?:na web|na internet|sobre)?\s*', '', user_text, flags=re.IGNORECASE).strip() or user_text
                search_res = search_web_tool(clean_query)
                results_list = WebSearchService.search_web(clean_query, max_results=2)
                if results_list:
                    top = results_list[0]
                    reply_text = f"Pesquisei na web sobre '{clean_query}': Segundo {top.get('title')}, {top.get('snippet')[:220]}."
                else:
                    reply_text = f"Pesquisei na internet por '{clean_query}', mas não encontrei novidades recentes agora."

            # B. Concluir Tarefa (Ex: "conclui a tarefa do café", "marca como feita a tarefa X")
            elif any(k in lower for k in ["conclui", "conclua", "concluir", "finaliza", "finalizar", "marca como feita", "marcar como feita", "marca como concluída", "feito o", "feita a"]) and any(w in lower for w in ["tarefa", "afazer", "café", "mercado", "relatório", "reunião", "comprar", "estudo", "pagar"]):
                target = re.sub(r'^(?:por favor,?\s*)?(?:bella,?\s*)?(?:conclui|conclua|concluir|finaliza|finalizar|marca como feita|marca como concluída)\s*(?:a\s*tarefa\s*(?:de|do|da)?)?\s*', '', user_text, flags=re.IGNORECASE).strip()
                target = target.replace("a tarefa", "").replace("o afazer", "").strip() or "tarefa"
                reply_text = complete_task_tool(target)

            # C. Remarcar / Editar Compromisso (Ex: "mude minha reunião das 15h para as 16h", "remarque o dentista para amanhã às 10h")
            elif any(k in lower for k in ["mude", "mudar", "remarque", "remarcar", "altere", "alterar", "troque", "trocar", "passe"]) and any(w in lower for w in ["reunião", "reuniao", "compromisso", "dentista", "médico", "treino", "almoço", "horário", "horario"]):
                # Tenta capturar novo horário ("para as 16h", "para 16:00", "às 14h")
                new_time_match = re.search(r'(?:para|p/)?\s*(?:às|as|à|a)?\s*(\d{1,2})(?:[:h](\d{2})|h)?', lower)
                new_time_str = "09:00"
                if new_time_match:
                    nh = int(new_time_match.group(1))
                    nm = int(new_time_match.group(2)) if new_time_match.group(2) else 0
                    new_time_str = f"{nh:02d}:{nm:02d}"

                new_date = "amanhã" if "amanhã" in lower else None
                # Termo de busca
                term_match = re.search(r'(?:minha|o|a)?\s*(reunião|reuniao|compromisso|dentista|médico|treino|almoço|pauta)\b', lower)
                target_term = term_match.group(1) if term_match else "reunião"
                reply_text = edit_calendar_event_tool(search_term=target_term, new_time=new_time_str, new_date_str=new_date)

            # D. Excluir Tarefa ou Compromisso (Ex: "apague a tarefa X", "exclua o compromisso Y")
            elif any(k in lower for k in ["apague", "apagar", "exclua", "excluir", "delete", "deletar", "remova", "remover"]):
                if "tarefa" in lower:
                    target = re.sub(r'^(?:por favor,?\s*)?(?:bella,?\s*)?(?:apague|exclua|delete|remova)\s*(?:a\s*tarefa\s*(?:de|do|da)?)?\s*', '', user_text, flags=re.IGNORECASE).strip() or "tarefa"
                    reply_text = delete_task_tool(target)
                else:
                    target = re.sub(r'^(?:por favor,?\s*)?(?:bella,?\s*)?(?:apague|exclua|delete|remova)\s*(?:o\s*compromisso\s*(?:de|do|da)?|a\s*reunião\s*(?:de|do|da)?)?\s*', '', user_text, flags=re.IGNORECASE).strip() or "compromisso"
                    reply_text = delete_calendar_event_tool(target)

            # E. Adicionar Compromisso
            elif any(k in lower for k in ["adicione", "adicionar", "agende", "agendar", "marque", "marcar", "coloque na agenda"]):
                time_tuple = ChatAssistantService.parse_time_string(lower)
                time_str = f"{time_tuple[0]:02d}:{time_tuple[1]:02d}"
                date_str = "amanhã" if "amanhã" in lower else "hoje"
                clean_title = re.sub(r'^(?:por favor,?\s*)?(?:bella,?\s*)?(?:adicione|agende|marque|coloque na agenda)\s*', '', user_text, flags=re.IGNORECASE).strip() or "Novo compromisso"
                cat = "health" if any(w in lower for w in ["treino", "academia", "médico", "dentista", "caminhada"]) else "work"
                is_prio = any(w in lower for w in ["urgente", "importante", "prioridade"])
                reply_text = add_calendar_event_tool(title=clean_title, date_str=date_str, time_str=time_str, category=cat, is_important=is_prio)

            # F. Adicionar Tarefa
            elif any(k in lower for k in ["tarefa", "afazer", "anote", "lembrete"]) and any(k in lower for k in ["crie", "criar", "adicione", "adicionar", "coloque", "anote"]):
                clean_title = re.sub(r'^(?:por favor,?\s*)?(?:bella,?\s*)?(?:adicione|adicionar|crie|criar|coloque|anote)\s*(?:uma\s*)?(?:tarefa|afazer|lembrete)?\s*(?:de|para)?\s*', '', user_text, flags=re.IGNORECASE).strip() or "Nova tarefa"
                prio = "high" if any(w in lower for w in ["urgente", "alta", "prioridade"]) else "medium"
                reply_text = add_task_tool(title=clean_title, priority=prio)

            # G. Consultar Agenda / Tarefas
            elif any(k in lower for k in ["agenda", "o que tenho", "compromissos", "quais tarefas", "o que fazer"]):
                target_date = "amanhã" if "amanhã" in lower else "hoje"
                reply_text = list_agenda_or_tasks_tool(item_type="all", date_str=target_date)

            # H. Clima
            elif any(k in lower for k in ["clima", "tempo", "chover", "chuva", "temperatura", "calor", "frio"]):
                reply_text = f"Em {city}, a previsão para hoje é de tempo {weather['condition'].lower()}, com temperatura atual de {weather['current_temp']}°C. A máxima chega a {weather['temp_max']}°C e a chance de chuva é de {weather['rain_prob']}%."

            # I. Cotação
            elif any(k in lower for k in ["dólar", "dolar", "cotação", "cotacao", "câmbio", "cambio"]):
                reply_text = f"O Dólar comercial está cotado a R$ {currency['bid']} para compra e R$ {currency['ask']} para venda, com variação de {currency['variation']}."

            else:
                reply_text = f"Oi! Eu sou a Bella, sua assistente pessoal! Posso pesquisar notícias na web, agendar ou remarcar compromissos, criar e concluir tarefas para você. Como posso te ajudar agora?"

        # Determina a ação primária executada para retornar ao frontend
        primary_action = executed_actions[-1] if executed_actions else None
        action_type = primary_action.get("type", "NONE") if primary_action else "NONE"

        # Salva resposta do assistente no banco
        assistant_msg = ChatMessage.objects.create(
            role='assistant',
            content=reply_text,
            action_type=action_type,
            action_details=json.dumps(primary_action or {})
        )

        return {
            "reply": reply_text,
            "action_type": action_type,
            "action_executed": primary_action,
            "all_actions": executed_actions,
            "message_id": assistant_msg.id,
            "created_at": assistant_msg.created_at.strftime("%H:%M")
        }

    @classmethod
    def process_message_stream(cls, user_text, api_key_override=None):
        """Processa a mensagem com resposta em streaming SSE (Server-Sent Events)"""
        import time
        import json

        pref = UserPreference.objects.first()
        api_key = api_key_override or (pref.gemini_api_key if pref and pref.gemini_api_key else None) or getattr(settings, "GEMINI_API_KEY", "")

        # Se houver chave Gemini, tenta fazer stream direto com o modelo
        if api_key and api_key.strip():
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key.strip())
                now = timezone.localtime()
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""Você é a Bella, assistente pessoal carismática, jovem, alegre e prestativa. Responda em português brasileiro de forma natural, calorosa e concisa.
Data/Hora atual: {now.strftime('%d/%m/%Y %H:%M')}.
Mensagem do usuário: {user_text}"""
                response = model.generate_content(prompt, stream=True)
                full_reply = ""
                for chunk in response:
                    if chunk.text:
                        full_reply += chunk.text
                        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk.text}, ensure_ascii=False)}\n\n"

                user_msg = ChatMessage.objects.create(role='user', content=user_text)
                asst_msg = ChatMessage.objects.create(role='assistant', content=full_reply, action_type="NONE")
                yield f"data: {json.dumps({'type': 'done', 'reply': full_reply, 'action_type': 'NONE', 'action_executed': None, 'message_id': asst_msg.id}, ensure_ascii=False)}\n\n"
                return
            except Exception as e:
                print(f"Erro no streaming Gemini: {e}")

        # Fallback estruturado com execução de ferramentas locais e streaming de tokens
        result = cls.process_message(user_text, api_key_override=api_key_override)
        reply = result.get("reply", "")

        words = reply.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"
            time.sleep(0.02)

        yield f"data: {json.dumps({'type': 'done', 'reply': reply, 'action_type': result.get('action_type', 'NONE'), 'action_executed': result.get('action_executed'), 'message_id': result.get('message_id')}, ensure_ascii=False)}\n\n"


class VoiceMemoService:
    """Processamento inteligente de memorandos e notas de voz com categorização por IA"""

    @staticmethod
    def process_memo(transcript_text: str) -> dict:
        import re
        import json
        clean = (transcript_text or "").strip()
        if not clean:
            return {"success": False, "error": "Transcrição vazia"}

        lower = clean.lower()
        now = timezone.localtime()
        intent = "note"
        action_taken = ""
        reply = ""
        created_item = None

        # 1. Detecta Compromisso de Agenda
        is_event = any(k in lower for k in ["reunião", "reuniao", "compromisso", "dentista", "médico", "medico", "consulta", "treino", "academia", "almoço", "almoco", "jantar", "aniversário", "aniversario", "marcar", "agendar"]) and (
            any(k in lower for k in ["às", "as", "horas", "amanhã", "amanha", "segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo", "hoje", "dia"])
        )

        # 2. Detecta Tarefa
        is_task = any(k in lower for k in ["tarefa", "lembrete", "lembrar de", "comprar", "pagar", "enviar", "fazer", "ligar para", "mandar", "organizar", "limpar", "consertar", "buscar", "levar"])

        if is_event and not is_task:
            intent = "event"
            time_tuple = ChatAssistantService.parse_time_string(lower)
            time_str = f"{time_tuple[0]:02d}:{time_tuple[1]:02d}"
            date_str = "amanhã" if ("amanhã" in lower or "amanha" in lower) else "hoje"
            target_date = ChatAssistantService.parse_date_string(date_str, now.date())
            target_dt = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time(*time_tuple)))

            clean_title = re.sub(r'^(?:por favor,?\s*)?(?:(?:anote|lembrete|gravar|memorando|agenda|agendar|marcar)\b\s*)?(?:\b(?:de|para)\b\s*)?', '', clean, flags=re.IGNORECASE).strip() or "Compromisso de Voz"
            category = "health" if any(w in lower for w in ["médico", "dentista", "treino", "saúde"]) else "work"

            ev = CalendarEvent.objects.create(
                title=clean_title,
                start_time=target_dt,
                category=category,
                description=f"Memorando gravado por voz: {clean}"
            )
            action_taken = f"Compromisso '{ev.title}' agendado para {target_date.strftime('%d/%m')} às {time_str}."
            reply = f"Perfeito! Agendei seu compromisso '{ev.title}' para {target_date.strftime('%d/%m')} às {time_str}."
            created_item = {"type": "event", "id": ev.id, "title": ev.title, "time": time_str, "date": target_date.strftime("%d/%m")}

        elif is_task:
            intent = "task"
            clean_title = re.sub(r'^(?:por favor,?\s*)?(?:(?:anote|lembrete|gravar|memorando|tarefa|lembrar de|comprar|fazer)\b\s*)?(?:\b(?:de|para)\b\s*)?', '', clean, flags=re.IGNORECASE).strip() or clean
            priority = "high" if any(w in lower for w in ["urgente", "alta", "prioridade", "importante"]) else "medium"
            cat = "personal" if any(w in lower for w in ["mercado", "comprar", "casa", "remédio", "remedio"]) else "work"

            task = QuickTask.objects.create(
                title=clean_title,
                priority=priority,
                category=cat,
                notes=f"Transcrição original: {clean}",
                due_date=now.date()
            )
            action_taken = f"Tarefa '{task.title}' criada na lista de afazeres."
            reply = f"Com certeza! Já criei a tarefa '{task.title}' na sua lista de afazeres!"
            created_item = {"type": "task", "id": task.id, "title": task.title, "priority": priority}

        else:
            intent = "note"
            clean_title = re.sub(r'^(?:por favor,?\s*)?(?:(?:anote|lembrete|gravar|memorando)\b\s*)?(?:\b(?:de|para)\b\s*)?', '', clean, flags=re.IGNORECASE).strip() or clean
            task = QuickTask.objects.create(
                title=clean_title[:80],
                priority="medium",
                category="study",
                notes=clean,
                due_date=now.date()
            )
            action_taken = f"Nota rápida salva: '{task.title}'."
            reply = f"Anotado! Salvei sua nota de voz com sucesso."
            created_item = {"type": "note", "id": task.id, "title": task.title}

        memo = VoiceMemo.objects.create(
            transcript=clean,
            intent_detected=intent,
            action_taken=action_taken,
            is_processed=True
        )

        return {
            "success": True,
            "memo_id": memo.id,
            "intent": intent,
            "action_taken": action_taken,
            "reply": reply,
            "item": created_item,
            "transcript": clean
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



