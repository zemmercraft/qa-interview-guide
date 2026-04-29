# Запуск проекта

## Что входит в проект

| Компонент | Описание |
|---|---|
| `index.html` + `*.md` | Статический гайд — открывается в браузере |
| `quiz.py` | Интерактивный тренажёр с оценкой ответов через LLM |
| `docker-compose.yml` | Оркестрация: веб-сервер + Ollama |
| `Dockerfile` | Образ для веб-сервера и квиза |

---

## Вариант 1. Docker Compose (рекомендуется)

### Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) или Docker Engine + Compose v2
- 5–10 GB свободного места (образ Ollama + модель)
- 8 GB RAM минимум (16 GB рекомендуется)

### Шаги

**1. Скачать проект**

```bash
git clone <repo-url> qa-interview-guide
cd qa-interview-guide
```

Или скопировать папку вручную на новую машину.

**2. Запустить веб-сервер и Ollama**

```bash
docker compose up -d web ollama
```

Гайд доступен: [http://localhost:8000](http://localhost:8000)

**3. Загрузить модель в Ollama (один раз)**

```bash
docker exec -it qa-interview-guide-ollama-1 ollama pull qwen2.5:7b
```

> Модель весит ~4.7 GB. Загружается один раз, хранится в Docker volume `ollama_data`.

Проверить что модель загружена:

```bash
docker exec -it qa-interview-guide-ollama-1 ollama list
```

**4. Запустить квиз с локальной LLM**

```bash
docker compose run --rm quiz
```

Квиз запустится внутри контейнера и подключится к Ollama по внутренней сети Docker (`http://ollama:11434`).

---

## Вариант 2. Локально без Docker

### Требования

- Python 3.9+
- [Ollama](https://ollama.com/download) установлен и запущен

### Шаги

**1. Установить зависимости**

```bash
pip install -r requirements.txt
```

**2. Запустить гайд**

```bash
python3 -m http.server 8000
```

Открыть в браузере: [http://localhost:8000](http://localhost:8000)

**3. Загрузить модель**

```bash
ollama pull qwen2.5:7b
```

**4. Запустить квиз**

```bash
# Локальная LLM (Ollama)
python3 quiz.py --local

# Альтернативная модель (быстрее, меньше RAM)
python3 quiz.py --local --model qwen2.5:3b

# Claude API (требует ключ)
export ANTHROPIC_API_KEY=sk-ant-...
python3 quiz.py
```

---

## Варианты моделей для Ollama

| Команда | RAM | Качество RU | Скорость CPU |
|---|---|---|---|
| `ollama pull qwen2.5:7b` | ~5 GB | ★★★★★ | медленно (~20–30 с) |
| `ollama pull qwen2.5:3b` | ~2.5 GB | ★★★★☆ | приемлемо (~8–12 с) |
| `ollama pull llama3.2:3b` | ~2.5 GB | ★★★☆☆ | быстро (~5–8 с) |
| `ollama pull mistral:7b` | ~5 GB | ★★★★☆ | медленно (~20–30 с) |

---

## Флаги quiz.py

```
python3 quiz.py [опции]

  --local                 Использовать Ollama вместо Claude API
  --model MODEL           Модель (default: qwen2.5:7b для --local,
                                   claude-haiku-4-5-20251001 для API)
  --ollama-url URL        URL Ollama (default: http://localhost:11434)
```

**Примеры:**

```bash
# Ollama на localhost
python3 quiz.py --local

# Ollama на другом хосте
python3 quiz.py --local --ollama-url http://192.168.1.10:11434

# Конкретная модель
python3 quiz.py --local --model mistral:7b

# Claude API с нестандартной моделью
python3 quiz.py --model claude-sonnet-4-6
```

---

## Управление Docker Compose

```bash
# Запустить всё
docker compose up -d web ollama

# Остановить
docker compose down

# Посмотреть логи
docker compose logs -f web

# Удалить всё включая данные Ollama
docker compose down -v
```

---

## Структура файлов

```
qa-interview-guide/
├── index.html              # Гайд (открывать в браузере)
├── quiz.py                 # Тренажёр
├── requirements.txt        # Python-зависимости
├── Dockerfile              # Образ для web + quiz
├── docker-compose.yml      # Оркестрация
└── md/
    ├── README.md
    ├── launch.md           # Этот файл
    ├── 01-testing-theory.md
    ├── 02-java-core.md
    ├── ...
    └── 16-soft-skills.md
```
