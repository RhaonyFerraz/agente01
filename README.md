# 📱 Assistente Pessoal Inteligente - PWA & Django com Google Gemini IA

Sistema moderno de assistência diária com foco em smartphones via **PWA (Progressive Web App)**, backend robusto em **Django**, integração com **Google Gemini Flash (gratuito)** e suporte a **bancos de dados na nuvem** (Supabase, Neon, PostgreSQL ou SQLite local).

---

## 🎯 Funcionalidades Principais

1. **✨ Resumo Executivo Inteligente (Gemini IA):**
   - Síntese diária automática no tom solicitado: cortês, objetivo, formatado em tópicos/bullet points com emojis elegantes.
   - Botão **"Ouvir este resumo"**: sintetizador de voz integrado (Web Speech API) para leitura em português brasileiro no smartphone.

2. **⛅ Previsão do Tempo em Tempo Real (Itobi - SP):**
   - Dados ao vivo via API Open-Meteo (temperatura atual, máxima, mínima, probabilidade de chuva, umidade e vento).
   - Suporte para alterar a cidade padrão pelas preferências.

3. **💵 Cotação do Dólar Comercial (USD/BRL):**
   - Cotação oficial via AwesomeAPI com valores de compra, venda, variação diária e conversor rápido interativo ($ ➔ R$).

4. **📅 Agenda de Compromissos:**
   - Lista cronológica de compromissos com categorias (Trabalho, Pessoal, Saúde, Estudos) e sinalização de prioridade alta.
   - Adição e sincronização direta pelo app ou pelo Django Admin.

5. **✉️ Caixa de Entrada & Destaques:**
   - Monitoramento de e-mails prioritários e alertas de ações necessárias.

6. **🎨 Sistema de Temas Dinâmicos pelo Django:**
   - O usuário escolhe o tema visual diretamente no app (5 temas premium pré-configurados: *Midnight Indigo*, *Cyberpunk Neon*, *Emerald Forest*, *Sunset Horizon*, *Titanium Minimal*).
   - Novos temas e paletas podem ser criados e gerenciados via **Django Admin**.

7. **📱 PWA Mobile-First Instalável:**
   - Funciona como aplicativo nativo em Android e iOS.
   - Ícones dedicados (192x192 e 512x512), Service Worker com cache offline e Web App Manifest.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.13, Django 6.1, Django REST Framework, Django CORS Headers.
- **Frontend PWA:** Vanilla JavaScript moderno, CSS3 com Glassmorphism e CSS Custom Properties reativas, HTML5 Semântico, Web Speech API (TTS).
- **Inteligência Artificial:** Google Gemini 1.5/2.0 Flash (`google-generativeai`) gratuito via Google AI Studio.
- **APIs de Dados:** Open-Meteo (Clima sem necessidade de token), AwesomeAPI (Câmbio USD/BRL).
- **Banco de Dados:** Suporte nativo a PostgreSQL na nuvem (Supabase / Neon / Render) ou SQLite local.
- **Controle de Versão:** Git & GitHub.

---

## 🚀 Como Executar o Projeto Localmente

### 1. Clonar o repositório e acessar a pasta
```bash
cd agente01
```

### 2. Ativar o Ambiente Virtual
- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Linux/Mac:**
  ```bash
  source venv/bin/activate
  ```

### 3. Instalar Dependências (se necessário)
```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente (`.env`)
Copie o arquivo `.env.example` para `.env` e preencha suas chaves caso deseje:
```ini
DEBUG=True
SECRET_KEY=sua-chave-secreta-django
ALLOWED_HOSTS=*

# Google Gemini AI (Gratuito via Google AI Studio):
# Obtenha em: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=

# Banco na Nuvem (Opcional - deixe vazio para SQLite local):
# DATABASE_URL=postgresql://postgres:senha@db.exemplo.supabase.co:5432/postgres

DEFAULT_CITY=Itobi, SP
DEFAULT_LAT=-21.7336
DEFAULT_LON=-46.9744
```

### 5. Executar as Migrações e Dados Iniciais
```bash
python manage.py migrate
python seed_data.py
```
> O script `seed_data.py` cadastra os 5 temas, dados de exemplo para hoje e cria o usuário administrador:
> - **Usuário:** `admin`
> - **Senha:** `admin123`

### 6. Iniciar o Servidor
```bash
python manage.py runserver 0.0.0.0:8000
```
- Acesse a aplicação PWA: [http://localhost:8000/](http://localhost:8000/)
- Acesse o painel Django Admin: [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

## 📲 Como Instalar o PWA no Celular

1. Conecte o celular na mesma rede Wi-Fi do computador e acesse `http://SEU_IP_LOCAL:8000/`.
2. **No Android (Google Chrome):**
   - O banner de instalação aparecerá no topo, ou toque no menu (⋮) > **"Adicionar à tela inicial"** / **"Instalar aplicativo"**.
3. **No iPhone (Safari):**
   - Toque no botão de compartilhamento (quadrado com seta para cima) > **"Adicionar à Tela de Início"**.

---

## ☁️ Conexão com Nuvem de Dados (Supabase / PostgreSQL)

Para usar banco de dados na nuvem:
1. Crie um projeto gratuito no [Supabase](https://supabase.com) ou [Neon](https://neon.tech).
2. Obtenha a Connection String URI (ex: `postgresql://postgres:...@...supabase.co:5432/postgres`).
3. Adicione no seu arquivo `.env`:
   ```env
   DATABASE_URL=postgresql://usuario:senha@host:5432/banco
   ```
4. Rode `python manage.py migrate` e `python seed_data.py`. Todos os temas, logs e agendas ficarão salvos na nuvem!

---

## 🐙 Como Publicar no GitHub

O repositório Git local já está inicializado na branch `main`. Para publicar no seu GitHub:

1. Crie um novo repositório vazio no seu GitHub (exemplo: `agente01`).
2. No terminal da pasta do projeto, execute:
   ```bash
   git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   git branch -M main
   git push -u origin main
   ```
