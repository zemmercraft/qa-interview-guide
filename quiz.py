#!/usr/bin/env python3
"""
QA Interview Quiz — интерактивный тренажёр по гайду qa-interview-guide.

Режим Claude API (по умолчанию):
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 quiz.py

Режим локальной LLM (Ollama):
    python3 quiz.py --local
    python3 quiz.py --local --model qwen2.5:3b
    python3 quiz.py --local --ollama-url http://localhost:11434

Режим локальной LLM внутри Docker Compose (сеть docker):
    python3 quiz.py --local --ollama-url http://ollama:11434
"""

import os
import re
import sys
import json
import random
import argparse
import textwrap
from pathlib import Path
from typing import List, Optional, Dict, Callable

# ── ANSI ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

GUIDE_DIR = Path(__file__).parent / "md"

CHAPTERS = [
    ("01", "Теория тестирования"),
    ("02", "Java Core"),
    ("03", "JUnit 5"),
    ("04", "Maven"),
    ("05", "Playwright Java"),
    ("06", "REST Assured"),
    ("07", "Spring для QA"),
    ("08", "Allure Report"),
    ("09", "Архитектура и паттерны"),
    ("10", "SQL и БД"),
    ("11", "Linux / Docker / K8s"),
    ("12", "CI/CD"),
    ("13", "Алгоритмы"),
    ("14", "System Design для QA"),
    ("15", "Fintech-специфика"),
    ("16", "Soft skills"),
]

Q_HEADER = re.compile(
    r"^### (?:Q\d+[a-z]?|Вопрос \d+)\. (.+)$",
    re.MULTILINE,
)

# ── Парсинг ───────────────────────────────────────────────────────────

def strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "[code example]", text)
    text = re.sub(r"`[^`]+`", lambda m: m.group(0)[1:-1], text)
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"^\s*[-|>]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_questions(md_path: Path) -> List[Dict]:
    text = md_path.read_text(encoding="utf-8")
    matches = list(Q_HEADER.finditer(text))
    questions = []
    for i, match in enumerate(matches):
        question = match.group(1).strip()
        if len(question) < 8:
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = strip_markdown(text[start:end].strip())[:2000]
        questions.append({
            "question": question,
            "content": content,
            "chapter_id": md_path.stem[:2],
        })
    return questions


def load_questions(chapter_filter: Optional[List[str]] = None) -> List[Dict]:
    all_q = []
    for num, _ in CHAPTERS:
        if chapter_filter and num not in chapter_filter:
            continue
        files = list(GUIDE_DIR.glob(f"{num}-*.md"))
        if files:
            all_q.extend(parse_questions(files[0]))
    return all_q


# ── Оценка ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a strict but fair QA interview coach evaluating a candidate's answer. "
    "Respond ONLY with valid JSON — no markdown fences, no extra text."
)

EVAL_TEMPLATE = """Question asked in the interview: {question}

Key points from the study guide (reference material):
{content}

Candidate's answer:
{user_answer}

Evaluate and respond with this exact JSON structure:
{{
  "score": <integer 0-3>,
  "verdict": "<one of: Отлично|Хорошо|Частично|Неверно>",
  "correct_points": ["list of things the candidate got right"],
  "missing_points": ["important things missing or stated incorrectly"],
  "model_answer": "correct answer in Russian, concise, 3-6 sentences with key facts"
}}

Score: 3=complete and accurate, 2=mostly correct but missing details, 1=partial or confused, 0=wrong/blank."""


def _parse_json(raw: str) -> Dict:
    raw = re.sub(r"^```(?:json)?\n?|\n?```$", "", raw.strip())
    return json.loads(raw)


def make_anthropic_caller(model: str = "claude-haiku-4-5-20251001") -> Callable:
    from anthropic import Anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"\n{RED}Ошибка: ANTHROPIC_API_KEY не задан.{RESET}")
        print(f"Запустите: {CYAN}export ANTHROPIC_API_KEY=sk-ant-...{RESET}")
        print(f"Или используйте локальный режим: {CYAN}python3 quiz.py --local{RESET}")
        sys.exit(1)
    client = Anthropic(api_key=api_key)

    def call(question: str, content: str, user_answer: str) -> Dict:
        msg = EVAL_TEMPLATE.format(
            question=question, content=content[:1500], user_answer=user_answer
        )
        response = client.messages.create(
            model=model,
            max_tokens=900,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": msg}],
        )
        return _parse_json(response.content[0].text)

    return call


def make_ollama_caller(model: str, ollama_url: str) -> Callable:
    try:
        from openai import OpenAI
    except ImportError:
        print(f"{RED}Установите openai: pip install openai{RESET}")
        sys.exit(1)

    client = OpenAI(base_url=f"{ollama_url.rstrip('/')}/v1", api_key="ollama")

    def call(question: str, content: str, user_answer: str) -> Dict:
        msg = EVAL_TEMPLATE.format(
            question=question, content=content[:1500], user_answer=user_answer
        )
        response = client.chat.completions.create(
            model=model,
            max_tokens=900,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": msg},
            ],
        )
        return _parse_json(response.choices[0].message.content)

    return call


# ── UI ────────────────────────────────────────────────────────────────

def score_color(score: int) -> str:
    return [RED, YELLOW, CYAN, GREEN][score]


def hr(char: str = "─", n: int = 58) -> str:
    return char * n


def print_result(result: Dict):
    color = score_color(result["score"])
    print(f"\n{color}{BOLD}{hr()}{RESET}")
    print(f"{color}{BOLD}  {result['verdict']}  ({result['score']}/3){RESET}")
    print(f"{color}{hr()}{RESET}")

    if result.get("correct_points"):
        print(f"\n{GREEN}✓ Правильно:{RESET}")
        for p in result["correct_points"]:
            print(f"  • {p}")

    if result.get("missing_points"):
        print(f"\n{YELLOW}⚠ Пропущено / неточно:{RESET}")
        for p in result["missing_points"]:
            print(f"  • {p}")

    print(f"\n{CYAN}{BOLD}Эталонный ответ:{RESET}")
    wrapped = textwrap.fill(
        result.get("model_answer", "—"),
        width=70, initial_indent="  ", subsequent_indent="  ",
    )
    print(wrapped)


def read_answer() -> str:
    print(f"\n{DIM}Введите ответ. Пустая строка = завершить:{RESET}")
    lines = []
    try:
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def chapter_menu() -> Optional[List[str]]:
    print(f"\n{BOLD}Выберите главы для тренировки:{RESET}")
    print(f"  {CYAN}0{RESET}  Все главы")
    for num, title in CHAPTERS:
        print(f"  {CYAN}{num}{RESET}  {title}")
    print(f"\n{DIM}Введите номера через пробел (пример: 01 02 05) или 0 для всех:{RESET}")
    raw = input("> ").strip()
    if not raw or raw == "0":
        return None
    valid = {num for num, _ in CHAPTERS}
    selected = [p.zfill(2) for p in raw.split() if p.zfill(2) in valid]
    return selected or None


def chapter_name(chapter_id: str) -> str:
    return next((t for n, t in CHAPTERS if chapter_id.startswith(n)), chapter_id)


# ── Аргументы ─────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="QA Interview Quiz — тренажёр собеседований"
    )
    parser.add_argument(
        "--local", action="store_true",
        help="Использовать локальную LLM через Ollama вместо Claude API",
    )
    parser.add_argument(
        "--model", default=None,
        help="Модель. Claude: 'claude-haiku-4-5-20251001'. Ollama: 'qwen2.5:7b' (default для --local)",
    )
    parser.add_argument(
        "--ollama-url", default="http://localhost:11434",
        help="URL Ollama-сервера (default: http://localhost:11434)",
    )
    return parser.parse_args()


# ── Главный цикл ──────────────────────────────────────────────────────

def main():
    args = parse_args()

    print(f"\n{BOLD}{CYAN}{hr('━')}{RESET}")
    print(f"{BOLD}{CYAN}   QA Interview Quiz — тренажёр собеседований{RESET}")

    if args.local:
        model = args.model or "qwen2.5:7b"
        print(f"{BOLD}{CYAN}   Режим: локальная LLM  │  {model}  │  {args.ollama_url}{RESET}")
        llm = make_ollama_caller(model, args.ollama_url)
    else:
        model = args.model or "claude-haiku-4-5-20251001"
        print(f"{BOLD}{CYAN}   Режим: Claude API  │  {model}{RESET}")
        llm = make_anthropic_caller(model)

    print(f"{BOLD}{CYAN}{hr('━')}{RESET}")

    chapter_filter = chapter_menu()
    questions = load_questions(chapter_filter)

    if not questions:
        print(f"{RED}Вопросы не найдены. Проверьте наличие .md файлов рядом со скриптом.{RESET}")
        sys.exit(1)

    random.shuffle(questions)
    print(f"\n{DIM}Загружено вопросов: {len(questions)}. Ctrl+C или 'q' — выход.{RESET}\n")

    total = 0
    total_score = 0

    for q in questions:
        total += 1
        print(f"{DIM}{hr()} Глава: {chapter_name(q['chapter_id'])} │ {total}/{len(questions)}{RESET}")
        print(f"\n{BOLD}{q['question']}{RESET}")

        user_answer = read_answer()

        if not user_answer:
            print(f"{YELLOW}Ответ пропущен.{RESET}")
            total -= 1
            continue

        print(f"\n{DIM}Оцениваю...{RESET}", end="", flush=True)

        try:
            result = llm(q["question"], q["content"], user_answer)
        except Exception as e:
            print(f"\r{RED}Ошибка оценки: {e}{RESET}")
            continue

        print("\r" + " " * 20 + "\r", end="")
        print_result(result)

        total_score += result["score"]
        max_so_far = total * 3
        pct = int(total_score / max_so_far * 100)
        print(f"\n{DIM}Счёт: {total_score}/{max_so_far} ({pct}%)  │  Enter — следующий, q — выход{RESET}")

        cmd = input("> ").strip().lower()
        if cmd in ("q", "quit", "exit", "й"):
            break
        print()

    max_possible = total * 3
    pct = int(total_score / max_possible * 100) if max_possible > 0 else 0
    color = GREEN if pct >= 80 else YELLOW if pct >= 50 else RED

    print(f"\n{BOLD}{color}{hr('━')}{RESET}")
    print(f"{BOLD}{color}  Итог сессии: {total_score}/{max_possible} ({pct}%){RESET}")
    if pct >= 80:
        print(f"{BOLD}{color}  Отличная подготовка!{RESET}")
    elif pct >= 50:
        print(f"{BOLD}{color}  Хорошо, но есть пробелы — повтори слабые главы.{RESET}")
    else:
        print(f"{BOLD}{color}  Нужно больше практики. Не сдавайся!{RESET}")
    print(f"{BOLD}{color}{hr('━')}{RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{DIM}Выход. До следующей тренировки!{RESET}\n")
