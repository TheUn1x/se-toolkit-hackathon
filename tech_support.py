"""
LLM Tech Support Module for MyBank
Uses local Qwen (Qwen Code CLI) for tech support
"""
import os
import logging
import subprocess
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


class TechSupportConfig:
    """Configuration for LLM tech support"""
    
    # LLM Provider: "qwen_cli", "http_api", or "faq"
    PROVIDER = os.getenv('LLM_PROVIDER', 'faq')  # Default to FAQ for reliability
    
    # Qwen CLI settings (not recommended - interactive mode)
    QWEN_MODEL = os.getenv('QWEN_MODEL', 'qwen3-coder-plus')
    QWEN_PATH = os.getenv('QWEN_PATH', '/home/theun1x/.nvm/versions/node/v20.20.2/bin/qwen')
    
    # HTTP API settings (for local LLM servers like Ollama, LM Studio, etc.)
    HTTP_API_URL = os.getenv('HTTP_API_URL', 'http://localhost:11434/api/chat')
    HTTP_API_MODEL = os.getenv('HTTP_API_MODEL', 'qwen2.5:7b')
    
    # Detect if running in WSL
    IS_WSL = os.path.exists('/proc/version') and 'microsoft' in open('/proc/version').read().lower()
    
    # System prompt for tech support
    SYSTEM_PROMPT = """Ты — технический специалист банка MyBank. Твоя задача — помогать пользователям с вопросами по работе Telegram-бота.

Основные возможности бота:
- /start - регистрация и главное меню
- /balance - проверка баланса
- /transfer - P2P переводы между пользователями (нужен PIN)
- /deposit - пополнение баланса (тестовое, без PIN)
- /withdraw - вывод средств (нужен PIN)
- /history - история всех операций
- /pin - установка/изменение PIN-кода
- /help - справка

Важная информация:
- PIN-код (4-6 цифр) нужен для переводов и выводов
- Пополнение работает мгновенно без PIN (тестовый режим)
- Лимит перевода: 1,000,000 ₽
- Лимит пополнения/вывода: 100,000 ₽
- P2P переводы мгновенные между пользователями MyBank
- Тестовые пользователи: ID 1 (Максим), ID 2 (Тест)

Отвечай кратко (2-3 предложения), дружелюбно и по делу. Используй эмодзи для наглядности. Если не знаешь ответа, честно скажи об этом."""


class FAQDatabase:
    """Simple FAQ database for fallback when LLM is unavailable"""
    
    def __init__(self):
        self.faqs = {
            'start': "/start — регистрирует вас в системе и показывает главное меню с балансом и кнопками управления 🏦",
            'balance': "/balance или кнопка 💰 показывает ваш текущий баланс",
            'transfer': "/transfer или 💸 — P2P перевод другому пользователю по ID. Требуется PIN-код 🔒",
            'deposit': "/deposit или 📥 — пополнение баланса. В тестовом режиме работает мгновенно без PIN ⚡",
            'withdraw': "/withdraw или 📤 — вывод средств. Требуется PIN. Доступны: Stub, Card, Crypto",
            'history': "/history или 📊 — показывает все операции: переводы, пополнения, выводы",
            'pin': "/pin или 🔒 — установить или изменить PIN-код (4-6 цифр). Нужен для переводов и выводов",
            'help': "/help — полная справка по всем командам бота",
            'cancel': "/cancel — отмена текущей операции",
            'p2p': "P2P переводы — мгновенные переводы между пользователями MyBank по ID. Введите ID, сумму, подтвердите PIN 💸",
            'limits': "📊 Лимиты:\n• Перевод: до 1,000,000 ₽\n• Пополнение: до 100,000 ₽\n• Вывод: до 100,000 ₽",
            'pin_code': "🔒 PIN-код — 4-6 значный код для подтверждения операций. Установите через /pin. Защищает переводы и выводы.",
            'test_users': "👥 Тестовые пользователи:\n• ID 1: Максим\n• ID 2: Тест\nИспользуйте ID 2 для тестирования переводов",
            'error': "❌ Если ошибка:\n1. Отмените: /cancel\n2. Начните заново\n3. Проверьте ввод",
            'default': "Я пока не могу ответить на этот вопрос. Попробуйте:\n• /help — список команд\n• Опишите проблему подробнее"
        }
    
    def find_answer(self, query: str) -> str:
        """Find relevant FAQ answer"""
        query_lower = query.lower()
        
        # Keyword matching
        for keyword, answer in self.faqs.items():
            if keyword in query_lower:
                return answer
        
        return self.faqs['default']


class QwenClient:
    """Tech support client with multiple backends"""
    
    def __init__(self):
        self.config = TechSupportConfig()
        self.faq = FAQDatabase()
        
        # Log which backend is being used
        if self.config.PROVIDER == 'http_api':
            logger.info(f"Using HTTP API for tech support: {self.config.HTTP_API_MODEL}")
        elif self.config.PROVIDER == 'qwen_cli':
            logger.warning("Qwen CLI mode - may be unreliable due to interactive nature")
            self.qwen_available = self._check_qwen()
            if not self.qwen_available:
                logger.info("Qwen CLI not available, falling back to FAQ")
        else:
            logger.info("Using FAQ database for tech support")
    
    def _check_qwen(self) -> bool:
        """Check if qwen command is available"""
        try:
            # If running in WSL, use direct path
            if self.config.IS_WSL:
                cmd = [self.config.QWEN_PATH, '--version']
            else:
                # If running in Windows, use wsl wrapper
                cmd = ['wsl', self.config.QWEN_PATH, '--version']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Qwen check failed: {e}")
            return False
    
    async def ask(self, question: str, context: dict = None) -> str:
        """Ask a question - uses configured backend"""
        
        # Build context-aware question
        user_context = ""
        if context:
            balance = context.get('balance', 0)
            has_pin = context.get('has_pin', False)
            user_context = f"\n\n[Контекст: баланс={balance:.2f} ₽, PIN={'установлен' if has_pin else 'не установлен'}]"
        
        try:
            if self.config.PROVIDER == 'http_api':
                return await self._ask_http_api(question + user_context)
            elif self.config.PROVIDER == 'qwen_cli' and getattr(self, 'qwen_available', False):
                return await self._ask_qwen(question + user_context)
            else:
                return self.faq.find_answer(question)
        except Exception as e:
            logger.error(f"LLM error ({self.config.PROVIDER}): {e}")
            return self.faq.find_answer(question)
    
    async def _ask_http_api(self, question: str) -> str:
        """Ask via HTTP API (Ollama, LM Studio, etc.)"""
        payload = {
            "model": self.config.HTTP_API_MODEL,
            "messages": [
                {"role": "system", "content": self.config.SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.config.HTTP_API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Handle different API response formats
            if 'message' in data:
                return data['message']['content']
            elif 'choices' in data:
                return data['choices'][0]['message']['content']
            else:
                return str(data)
    
    async def _ask_qwen(self, question: str) -> str:
        """Ask Qwen via CLI"""
        
        # Build full prompt with system instructions
        full_prompt = f"{self.config.SYSTEM_PROMPT}\n\nВопрос пользователя: {question}"
        
        # If running in WSL, use direct path
        if self.config.IS_WSL:
            cmd = [self.config.QWEN_PATH, '-p', full_prompt, '-o', 'text', '--yolo']
        else:
            # If running in Windows, use wsl wrapper
            cmd = ['wsl', self.config.QWEN_PATH, '-p', full_prompt, '-o', 'text', '--yolo']
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            response = result.stdout.strip()
            logger.info(f"Qwen response: {response[:100]}...")
            return response
        else:
            raise Exception(f"Qwen CLI error: {result.stderr}")


# Global LLM client instance
llm_client = QwenClient()
