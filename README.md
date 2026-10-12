# 🚀 Antigravity Studio

Умный десктопный оркестратор и среда тестирования/разработки для проектов **Antigravity** с паттерном **Supervisor-Worker (Gemini Tech Lead + Antigravity Developer)**, встроенным симулятором движений, песочницей тестов и Git Ops.

---

## 🌟 Возможности и Архитектура

1. **Supervisor-Worker Паттерн (Tech Lead + Developer):**
   * **Gemini Tech Lead:** Принимает быстрый запрос на русском языке, анализирует дерево файлов и декомпозирует задачу в строгую англоязычную спецификацию.
   * **Экономия токенов до 70%:** Перевод на английский язык сжимает токены в 2 раза (BPE кириллица vs латиница), а точечная локализация файлов исключает слепое блуждание агента по репозиторию.
   * **Antigravity Worker:** Выполняет задачу автономно через CLI `agy.exe` или Python SDK, стримит мысли (**Thinking**), вызовы инструментов (**Tools**) и токены через WebSocket в реальном времени.

2. **Готовые шаблоны (Playbooks):**
   * Создание нового Босса / Рейда (баланс, уязвимости, спрайты, диалоги).
   * Новая кинетическая детекция и античит (эвристика вариативности).
   * Платёжные офферы и защита от двойных списаний (Telegram Stars).
   * Стримерские OBS-виджеты и WebSocket-события.
   * Комплексный прогон тестов (QA).

3. **Среда тестирования и песочница (Testing & Sandbox):**
   * **Backend Test Runner:** Запуск Jest / npm test / pytest в один клик с подсветкой упавших тестов.
   * **Motion & Pose Simulator:** Синтетический симулятор траекторий суставов (приседания и отжимания) для проверки математики подсчета повторов без камеры.
   * **Narrative & Lore Validator:** Проверка схемы и целостности JSON-файлов сюжета (`splash_quotes.json`, `boss_dialogues.json`, `store_items_copy.json`).
   * **Live Dev Server:** Локальный запуск предпросмотра TMA / веб-версии прямо из студии.

4. **Git Ops & GitHub Sync:**
   * Просмотр текущей ветки, измененных файлов и `git diff`.
   * Commit & Push в репозиторий GitHub (`RLafleet`) в один клик.

---

## 🖥️ Быстрый запуск

### Способ 1: Двойной клик
Запустите файл **`run.bat`**.

### Способ 2: Через терминал
```bash
python main.py
```
*(Для открытия в обычном браузере: `python main.py --browser`)*

---

## ⚙️ Структура проекта

```
antigravity-studio/
├── main.py            # Точка входа, запуск FastAPI и PyWebView окна
├── server.py          # REST & WebSocket API
├── spec_architect.py  # Gemini Tech Lead & Playbooks
├── worker_engine.py   # Исполнение задач (Antigravity CLI / SDK)
├── test_engine.py     # Тест-раннер, симулятор поз, валидатор лора
├── git_manager.py     # Git Ops (diff, commit, push)
├── gemini_client.py   # Клиент Gemini API (3.8 Flash, 3.1 Pro)
├── config.py          # Управление конфигурацией (~/.antigravity_studio/)
├── web/
│   └── index.html     # Dark-theme интерфейс на Tailwind CSS
├── requirements.txt   # Зависимости Python
├── run.bat            # Скрипт запуска для Windows
└── README.md          # Документация
```

---

## 🔑 Первоначальная настройка

1. Перейдите во вкладку **«Настройки» (⚙️)**.
2. Укажите ваш **Gemini API Key** (поддерживается автоподхват ключа).
3. Выберите рабочую директорию проекта через кнопку **«Обзор»**.
