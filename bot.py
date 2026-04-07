"""
CashFlow - Telegram Bot for Shared Expenses
Full-featured bot with groups, step-by-step expense dialogs, settlements, and notifications
"""
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from cashflow_api import CashFlowAPI
from tech_support import llm_client

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cashflow.log')
    ]
)
logger = logging.getLogger(__name__)

# Conversation states
STATE_EXPENSE_AMOUNT = 1
STATE_EXPENSE_DESCRIPTION = 2
STATE_EXPENSE_CATEGORY = 3
STATE_EXPENSE_SPLIT_TYPE = 4
STATE_EXPENSE_PARTICIPANTS = 5
STATE_SETTLE_TARGET = 6
STATE_SUPPORT_QUESTION = 7
STATE_ADD_USER_NAME = 8
STATE_PARTIAL_AMOUNT = 9
STATE_SELECT_PAYER = 10
STATE_CREATE_GROUP_NAME = 11
STATE_CREATE_GROUP_DESC = 12
STATE_SELECT_GROUP = 13
STATE_SELECT_EXPENSE_GROUP = 14

# Category choices
CATEGORIES = {
    'food': '🍔 Еда',
    'transport': '🚗 Транспорт',
    'housing': '🏠 Жильё',
    'entertainment': '🎬 Развлечения',
    'utilities': '💡 Коммунальные',
    'groceries': '🛒 Продукты',
    'other': '📦 Другое',
}

# Get bot token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Initialize CashFlow API
cf = CashFlowAPI()


def safe_md(text: str) -> str:
    """Escape Markdown v2 special characters"""
    if not text:
        return ''
    for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        text = text.replace(char, f'\\{char}')
    return text


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, custom_text: str = None):
    """Show main menu with buttons"""
    user = cf.get_user(update.effective_user.id)

    if not user:
        await update.effective_message.reply_text("❌ Пользователь не найден. Используйте /start")
        return ConversationHandler.END

    if custom_text:
        menu_text = custom_text
    else:
        safe_name = safe_md(user.first_name)
        groups = cf.get_user_groups(user.id)
        group_count = len(groups)

        menu_text = (
            f"💰 *CashFlow \\- Управление тратами*\n\n"
            f"👤 {safe_name} \\(ID: {user.id}\\)\n"
            f"👥 Групп: {group_count}\n\n"
            "Выберите действие:"
        )

    keyboard = [
        [InlineKeyboardButton("➕ Добавить трату", callback_data='add_expense')],
        [InlineKeyboardButton("👥 Группы", callback_data='groups_menu')],
        [InlineKeyboardButton("📊 Мои балансы", callback_data='balances')],
        [InlineKeyboardButton("💸 Погасить долг", callback_data='settle')],
        [InlineKeyboardButton("📜 История", callback_data='history')],
        [InlineKeyboardButton("🔗 Привязать аккаунт", callback_data='link_account')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(menu_text, parse_mode='MarkdownV2')
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    logger.info(f"User {user.first_name} ({user.id}) started bot")

    username = user.username
    invited_by = None

    if username:
        pending_invites = context.bot_data.get('pending_invites', {})
        if username in pending_invites:
            invite_info = pending_invites[username]
            invited_by = invite_info['inviter_name']
            del pending_invites[username]

    # Register or activate user
    if username:
        activated_user = cf.activate_pending_user(username, user.id, user.first_name)
        if not activated_user:
            cf.register_user(
                telegram_id=user.id,
                first_name=user.first_name,
                username=username,
                last_name=user.last_name,
            )
    else:
        cf.register_user(
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
            last_name=user.last_name,
        )

    # Ensure settings
    current_user = cf.get_user(user.id)
    if current_user:
        cf.get_or_create_settings(current_user.id)

    if invited_by:
        safe_inviter = safe_md(invited_by)
        welcome_text = (
            f"👋 Добро пожаловать, {safe_md(user.first_name)}\\!\n\n"
            f"📨 Вас пригласил\\(а\\) {safe_inviter}\n"
            f"для учёта совместных трат\n\n"
            f"💰 *CashFlow* \\- бот для совместных расходов\n\n"
            "Выберите действие:"
        )
    else:
        welcome_text = (
            f"👋 Добро пожаловать, {safe_md(user.first_name)}\\!\n\n"
            f"💰 *CashFlow* \\- бот для совместных расходов\n\n"
            "Выберите действие:"
        )

    await show_main_menu(update, context, welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "💰 *CashFlow \\- Справка*\n\n"
        "*Как это работает\\:*\n"
        "1\\. Создайте группу или добавьте трату\n"
        "2\\. Бот автоматически считает балансы\n"
        "3\\. Погасите долг в любой момент\n\n"
        "*Команды\\:*\n"
        "/start \\- Главное меню\n"
        "/balance \\- Мой общий баланс\n"
        "/groups \\- Мои группы\n"
        "/add \\- Добавить трату\n"
        "/settle \\- Погасить долг\n"
        "/history \\- Последние 10 трат\n"
        "/optimize \\- Оптимизировать выплаты\n"
        "/support \\- Техподдержка\n"
        "/help \\- Эта справка\n\n"
        "*Пример\\:*\n"
        "Вы заплатили 300₽ за ужин вдвоём\n"
        "→ Ваш счёт: \\+150₽\n"
        "→ Друг: \\-150₽"
    )

    await update.message.reply_text(help_text, parse_mode='MarkdownV2')


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command - show total balance across all groups"""
    user = cf.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return

    total = cf.get_user_total_balance(user.id)
    balances = cf.get_user_balances(user.id)

    text = f"📊 *Общий баланс для {safe_md(user.first_name)}*\n\n"
    text += f"💚 Вам должны: *{total['total_owed']:.2f} ₽*\n"
    text += f"❤️ Вы должны: *{total['total_owes']:.2f} ₽*\n"
    text += f"📈 Нетто: *{total['net']:+.2f} ₽*\n\n"

    if balances:
        text += "*Детализация\\:*\n"
        for b in balances:
            emoji = "💚" if b['amount'] > 0 else "❤️"
            text += f"{emoji} {safe_md(b['user'])}: *{b['amount']:+.2f} ₽*\n"
    else:
        text += "✅ Пока нет долгов"

    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /groups command"""
    user = cf.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return

    groups = cf.get_user_groups(user.id)

    if not groups:
        await update.message.reply_text(
            "👥 *У вас пока нет групп*\n\n"
            "Создайте группу через главное меню",
            parse_mode='MarkdownV2'
        )
        return

    text = "👥 *Мои группы*\n\n"
    for g in groups:
        members = cf.get_group_members(g.id)
        archived = " 📦 (архив)" if g.is_archived else ""
        text += f"• *{safe_md(g.name)}*{archived} \\- {len(members)} уч\\.\n"

    text += "\nВыберите группу в главном меню для подробностей"

    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command - show last 10 expenses"""
    user = cf.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return

    expenses = cf.get_user_expenses(user.id, limit=10)

    if not expenses:
        await update.message.reply_text(
            "📜 *История пуста*\n\n"
            "Добавьте первую трату через /add",
            parse_mode='MarkdownV2'
        )
        return

    text = "📜 *Последние 10 трат*\n\n"

    for e in expenses:
        amount = e.amount
        description = e.description or 'Без описания'
        created_at = e.expense_date or e.created_at
        split_count = len(e.splits) if hasattr(e, 'splits') and e.splits else 1
        payer_name = e.payer.first_name if hasattr(e, 'payer') and e.payer else 'Unknown'

        text += f"💰 *{amount:.2f} ₽* \\- {safe_md(description)}\n"
        text += f"  Заплатил: {safe_md(payer_name)}\n"
        text += f"  Разделено на {split_count} чел\\.\n"
        text += f"  📅 {safe_md(str(created_at).split('.')[0])}\n\n"

    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def optimize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /optimize command - show optimized settlement plan"""
    user = cf.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return

    plan = cf.get_optimized_settlements(user_id=user.id)

    if not plan:
        await update.message.reply_text(
            "🧠 *Оптимизация*\n\n"
            "✅ Вам не нужно ни платить, ни получать — всё рассчитано!",
            parse_mode='MarkdownV2'
        )
        return

    text = "🧠 *Оптимальный план выплат*\n\n"
    for p in plan:
        text += f"💸 {safe_md(p['from_user_name'])} → {safe_md(p['to_user_name'])}: *{p['amount']:.2f} ₽*\n"

    text += f"\nВсего транзакций: *{len(plan)}*"

    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /support command"""
    question = ' '.join(context.args) if context.args else ''

    if not question:
        await update.message.reply_text(
            "🤖 *Техподдержка CashFlow*\n\n"
            "Задайте вопрос:\n\n"
            "Примеры:\n"
            "• Как добавить трату?\n"
            "• Как посмотреть баланс?\n"
            "• Что значит 'в плюсе'?\n\n"
            "Используйте: /support ваш_вопрос",
            parse_mode='MarkdownV2'
        )
        return

    user = cf.get_user(update.effective_user.id)
    context_data = {
        'balance': 0,
        'has_pin': True
    }

    await update.message.reply_chat_action('typing')
    answer = await llm_client.ask(question, context_data)

    await update.message.reply_text(
        f"🤖 *Поддержка*\n\n{answer}",
        parse_mode='MarkdownV2'
    )


# ==================== GROUPS MENU ====================

async def groups_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show groups menu"""
    query = update.callback_query
    await query.answer()

    user = cf.get_user(update.effective_user.id)
    if not user:
        await query.message.reply_text("❌ Пользователь не найден")
        return ConversationHandler.END

    groups = cf.get_user_groups(user.id)

    keyboard = [
        [InlineKeyboardButton("➕ Создать группу", callback_data='create_group')],
    ]

    for g in groups:
        if not g.is_archived:
            keyboard.append([InlineKeyboardButton(
                f"📁 {g.name}",
                callback_data=f'view_group_{g.id}'
            )])

    keyboard.append([InlineKeyboardButton("← Назад", callback_data='back_to_menu')])

    await query.message.reply_text(
        "👥 *Группы*\n\n"
        "Выберите группу или создайте новую:",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END


async def create_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start creating a group"""
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "👥 *Создать группу*\n\n"
        "Введите название группы:",
        parse_mode=None
    )
    return STATE_CREATE_GROUP_NAME


async def create_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get group name"""
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Название слишком короткое (мин. 2 символа):")
        return STATE_CREATE_GROUP_NAME

    context.user_data['group_name'] = name

    await update.message.reply_text(
        "📝 Введите описание (необязательно):\n"
        "Напишите '-' для пропуска",
    )
    return STATE_CREATE_GROUP_DESC


async def create_group_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish creating group"""
    desc = update.message.text if update.message.text != '-' else None
    name = context.user_data['group_name']

    user = cf.get_user(update.effective_user.id)
    group = cf.create_group(name, user.id, desc)

    if group:
        await update.message.reply_text(
            f"✅ Группа *{name}* создана!\n\n"
            f"Теперь пригласите участников через /add_user",
            parse_mode=None
        )
    else:
        await update.message.reply_text("❌ Ошибка при создании группы")

    context.user_data.clear()
    return await show_main_menu(update, context)


async def view_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View group details"""
    query = update.callback_query
    await query.answer()

    group_id = int(query.data.replace('view_group_', ''))
    group = cf.get_group(group_id)

    if not group:
        await query.message.reply_text("❌ Группа не найдена")
        return ConversationHandler.END

    members = cf.get_group_members(group_id)
    balances = cf.get_group_balances(group_id)

    text = f"📁 *{group.name}*\n"
    if group.description:
        text += f"{group.description}\n"
    text += f"\n👥 Участников: {len(members)}\n\n"

    text += "*Участники\\:*\n"
    for m in members:
        text += f"• {safe_md(m.first_name)}\n"

    if balances:
        text += "\n*Балансы\\:*\n"
        for b in balances:
            text += f"• {safe_md(b['debtor_name'])} должен {safe_md(b['creditor_name'])}: *{b['amount']:.2f} ₽*\n"
    else:
        text += "\n✅ Все рассчиты"

    keyboard = [
        [InlineKeyboardButton("📜 Траты группы", callback_data=f'group_expenses_{group_id}')],
        [InlineKeyboardButton("🚪 Покинуть группу", callback_data=f'leave_group_{group_id}')],
        [InlineKeyboardButton("← Назад", callback_data='groups_menu')],
    ]

    await query.message.reply_text(text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


async def group_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show group expenses"""
    query = update.callback_query
    await query.answer()

    group_id = int(query.data.replace('group_expenses_', ''))
    group = cf.get_group(group_id)
    expenses = cf.get_group_expenses(group_id, limit=20)

    if not expenses:
        await query.message.reply_text("📜 В группе пока нет трат")
        return ConversationHandler.END

    text = f"📜 *Траты группы {safe_md(group.name)}*\n\n"
    for e in expenses:
        payer = e.payer.first_name if hasattr(e, 'payer') and e.payer else 'Unknown'
        text += f"💰 *{e.amount:.2f} ₽* \\- {safe_md(e.description or 'Без описания')}\n"
        text += f"  Заплатил: {safe_md(payer)}\n"
        text += f"  📅 {safe_md(str(e.expense_date).split('.')[0])}\n\n"

    keyboard = [[InlineKeyboardButton("← Назад", callback_data=f'view_group_{group_id}')]]
    await query.message.reply_text(text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


async def leave_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Leave a group"""
    query = update.callback_query
    await query.answer()

    group_id = int(query.data.replace('leave_group_', ''))
    user = cf.get_user(update.effective_user.id)

    success, message = cf.remove_group_member(group_id, user.id)

    if success:
        await query.message.reply_text(f"✅ {message}")
    else:
        await query.message.reply_text(f"❌ {message}")

    context.user_data.clear()
    return await show_main_menu(update, context)


# ==================== ADD USER ====================

async def add_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding new participant"""
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "👥 *Добавить участника*\n\n"
        "Введите @username участника в Telegram:\n"
        "(например: @ivan_petrov)",
        parse_mode=None
    )
    return STATE_ADD_USER_NAME


async def add_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new user by username"""
    username = update.message.text.strip()

    if username.startswith('@'):
        username = username[1:]

    if len(username) < 3:
        await update.message.reply_text(
            "❌ Username слишком короткий\n"
            "Введите @username (минимум 3 символа):"
        )
        return STATE_ADD_USER_NAME

    existing_user = cf.get_user_by_username(username)
    if existing_user:
        await update.message.reply_text(
            f"⚠️ Участник @{username} уже есть в системе\n"
            f"👤 {existing_user.first_name} (ID: {existing_user.id})"
        )
        return await show_main_menu(update, context)

    cf.register_pending_user(username)

    inviter = cf.get_user(update.effective_user.id)

    context.bot_data.setdefault('pending_invites', {})[username] = {
        'inviter_id': inviter.id,
        'inviter_name': inviter.first_name
    }

    await update.message.reply_text(
        f"✅ Участник запрошен!\n\n"
        f"👤 @{username}\n\n"
        f"📩 Когда @{username} запустит бота (/start),\n"
        f"он получит приглашение от {inviter.first_name}",
        parse_mode=None
    )

    return await show_main_menu(update, context)


# ==================== EXPENSE FLOW ====================

async def add_expense_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding expense"""
    query = update.callback_query
    await query.answer()

    users = cf.get_all_users()
    if len(users) < 2:
        await query.message.reply_text(
            "⚠️ Нужно минимум 2 пользователя для трат\n\n"
            "Пригласите друга или создайте второго пользователя"
        )
        return ConversationHandler.END

    # Select group first
    user = cf.get_user(update.effective_user.id)
    groups = cf.get_user_groups(user.id)

    keyboard = []
    if groups:
        keyboard.append([InlineKeyboardButton("🚫 Без группы", callback_data='expense_group_none')])
        for g in groups:
            if not g.is_archived:
                keyboard.append([InlineKeyboardButton(
                    f"📁 {g.name}",
                    callback_data=f'expense_group_{g.id}'
                )])
    else:
        keyboard.append([InlineKeyboardButton("🚫 Без группы", callback_data='expense_group_none')])

    await query.message.reply_text(
        "➕ Добавить трату\n\n"
        "Выберите группу (или 'Без группы'):",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return STATE_SELECT_EXPENSE_GROUP


async def select_expense_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select group for expense"""
    query = update.callback_query
    await query.answer()

    if query.data == 'expense_group_none':
        context.user_data['expense_group_id'] = None
    else:
        group_id = int(query.data.replace('expense_group_', ''))
        context.user_data['expense_group_id'] = group_id

    # Now select payer
    users = cf.get_all_users()
    keyboard = []
    for u in users:
        emoji = "🟢" if u.telegram_id == update.effective_user.id else "⚪"
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {u.first_name}",
            callback_data=f'payer_{u.id}'
        )])

    await query.message.reply_text(
        "Кто заплатил?",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return STATE_SELECT_PAYER


async def select_payer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select who paid"""
    query = update.callback_query
    await query.answer()

    payer_id = int(query.data.replace('payer_', ''))
    context.user_data['payer_id'] = payer_id

    payer = cf.get_user_by_internal_id(payer_id)
    context.user_data['payer_name'] = payer.first_name

    await query.message.reply_text(
        f"💰 Платит: *{payer.first_name}*\n\n"
        "Введите сумму (₽):",
        parse_mode=None
    )
    return STATE_EXPENSE_AMOUNT


async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enter expense amount"""
    try:
        amount = float(update.message.text.replace(',', '.'))

        if amount <= 0:
            await update.message.reply_text(
                "❌ Сумма должна быть больше 0\n"
                "Введите сумму:"
            )
            return STATE_EXPENSE_AMOUNT

        context.user_data['amount'] = amount

        await update.message.reply_text(
            "📝 Описание (необязательно):\n"
            "Напишите '-' для пропуска",
        )
        return STATE_EXPENSE_DESCRIPTION

    except ValueError:
        await update.message.reply_text(
            "❌ Введите число, например: 500\n"
            "Введите сумму:"
        )
        return STATE_EXPENSE_AMOUNT


async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enter expense description"""
    description = update.message.text if update.message.text != '-' else None
    context.user_data['description'] = description

    # Show category selection
    keyboard = []
    row = []
    for key, label in CATEGORIES.items():
        row.append(InlineKeyboardButton(label, callback_data=f'cat_{key}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await update.message.reply_text(
        "📂 Выберите категорию:",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return STATE_EXPENSE_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select expense category"""
    query = update.callback_query
    await query.answer()

    category = query.data.replace('cat_', '')
    context.user_data['category'] = category

    # Show split type selection
    keyboard = [
        [InlineKeyboardButton("⚖️ Поровну", callback_data='split_equal')],
        [InlineKeyboardButton("📊 По процентам", callback_data='split_percent')],
        [InlineKeyboardButton("💵 По точным суммам", callback_data='split_exact')],
    ]

    await query.message.reply_text(
        "Как разделить трату?",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return STATE_EXPENSE_SPLIT_TYPE


async def select_split_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select split type"""
    query = update.callback_query
    await query.answer()

    split_type = query.data.replace('split_', '')
    context.user_data['split_type'] = split_type

    if split_type in ('percent', 'exact'):
        # For percent/exact, we need manual shares - but for simplicity in Telegram,
        # we'll just do equal split with participant selection
        # Full percent/exact support is in the web UI
        pass

    # Select participants
    payer_id = context.user_data['payer_id']
    users = cf.get_all_users()
    participants = [u for u in users if u.id != payer_id]

    if not participants:
        await query.message.reply_text("❌ Нет участников для разделения")
        context.user_data.clear()
        return ConversationHandler.END

    keyboard = []
    for u in participants:
        keyboard.append([InlineKeyboardButton(
            f"✅ {u.first_name}",
            callback_data=f'part_toggle_{u.id}'
        )])

    keyboard.append([InlineKeyboardButton("➕ Все выбраны — добавить трату", callback_data='add_expense_confirm')])

    # Store selected participants (all by default)
    context.user_data['selected_participants'] = [u.id for u in participants]

    await query.message.reply_text(
        "Выберите участников (все выбраны по умолчанию):",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return STATE_EXPENSE_PARTICIPANTS


async def toggle_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle participant selection"""
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.replace('part_toggle_', ''))
    selected = context.user_data.get('selected_participants', [])

    if user_id in selected:
        selected.remove(user_id)
    else:
        selected.append(user_id)

    context.user_data['selected_participants'] = selected

    # Update keyboard
    users = cf.get_all_users()
    payer_id = context.user_data['payer_id']
    participants = [u for u in users if u.id != payer_id]

    keyboard = []
    for u in participants:
        checked = "✅" if u.id in selected else "⬜"
        keyboard.append([InlineKeyboardButton(
            f"{checked} {u.first_name}",
            callback_data=f'part_toggle_{u.id}'
        )])

    selected_count = len(selected)
    keyboard.append([InlineKeyboardButton(
        f"➕ Выбрано: {selected_count} — добавить трату",
        callback_data='add_expense_confirm'
    )])

    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_EXPENSE_PARTICIPANTS


async def confirm_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and add expense"""
    query = update.callback_query
    await query.answer()

    payer_id = context.user_data['payer_id']
    amount = context.user_data['amount']
    description = context.user_data.get('description')
    category = context.user_data.get('category', 'other')
    split_type = context.user_data.get('split_type', 'equal')
    group_id = context.user_data.get('expense_group_id')
    participant_ids = context.user_data.get('selected_participants', [])

    if not participant_ids:
        await query.message.reply_text("❌ Нужен хотя бы один участник")
        context.user_data.clear()
        return await show_main_menu(update, context)

    result, error = cf.add_expense(
        payer_id=payer_id,
        amount=amount,
        split_type=split_type,
        participant_ids=participant_ids,
        description=description,
        category=category,
        group_id=group_id,
    )

    if not result:
        await query.message.reply_text(f"❌ {error}")
        context.user_data.clear()
        return await show_main_menu(update, context)

    payer_name = context.user_data['payer_name']
    total_people = len(participant_ids) + 1
    per_person = amount / total_people

    group_name = ""
    if group_id:
        group = cf.get_group(group_id)
        if group:
            group_name = f"\n📁 Группа: {group.name}"

    result_text = (
        f"✅ Трата добавлена!\n\n"
        f"💰 Сумма: *{amount:.2f} ₽*\n"
        f"👤 Заплатил: {payer_name}\n"
        f"📝 {description or 'Без описания'}\n"
        f"📂 {CATEGORIES.get(category, category)}\n"
        f"👥 Разделено на {total_people} человек{group_name}\n"
        f"📊 По {per_person:.2f} ₽ с человека\n"
    )

    await query.message.reply_text(result_text, parse_mode=None)

    # TODO: Send notifications to participants
    # For each participant, if they have telegram_id, notify them

    context.user_data.clear()
    return await show_main_menu(update, context)


# ==================== BALANCES ====================

async def show_balances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all balances"""
    query = update.callback_query
    await query.answer()

    user_id = cf.get_user(update.effective_user.id).id
    balances = cf.get_user_balances(user_id)

    if not balances:
        await query.message.reply_text(
            "📊 *Общие счёта*\n\n"
            "Пока нет трат\n\n"
            "Добавьте первую трату ➕",
            parse_mode='MarkdownV2'
        )
        return

    user_name = cf.get_user(update.effective_user.id).first_name

    text = f"📊 *Общие счёта для {safe_md(user_name)}*\n\n"

    for b in balances:
        if b['amount'] > 0:
            status = "🟢 В ПЛЮСЕ"
            emoji = "↑"
        elif b['amount'] < 0:
            status = "🔴 В МИНУСЕ"
            emoji = "↓"
        else:
            status = "⚪ Расчёт"
            emoji = "="

        text += f"*{safe_md(b['user'])}*\n"
        text += f"  {emoji} {status}\n"
        text += f"  Счёт: `{b['amount']:+.2f} ₽`\n\n"

    text += "\n💡 Положительный счёт = вам должны\n💡 Отрицательный = вы должны"

    await query.message.reply_text(text, parse_mode='MarkdownV2')
    return await show_main_menu(update, context)


# ==================== SETTLE ====================

async def settle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settle options"""
    query = update.callback_query
    await query.answer()

    user_id = cf.get_user(update.effective_user.id).id
    balances = cf.get_user_balances(user_id)

    people_you_owe = [b for b in balances if b['amount'] < 0]

    if not people_you_owe:
        await query.message.reply_text(
            "💚 Всё рассчитано!\n\n"
            "Вы никому не должны"
        )
        return await show_main_menu(update, context)

    keyboard = []
    for b in people_you_owe:
        debt = abs(b['amount'])
        keyboard.append([
            InlineKeyboardButton(
                f"💸 {b['user']} ({debt:.2f} ₽)",
                callback_data=f'settle_full_{b["user_id"]}'
            ),
            InlineKeyboardButton(
                f"💵 Частично",
                callback_data=f'settle_partial_{b["user_id"]}'
            )
        ])

    keyboard.append([InlineKeyboardButton("← Назад", callback_data='back_to_menu')])

    await query.message.reply_text(
        "💸 Погасить долг\n\n"
        "💸 = погасить полностью\n"
        "💵 = частичное погашение\n\n"
        "Выберите кому заплатить:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return STATE_SETTLE_TARGET


async def settle_target_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settle target selection"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('settle_full_'):
        target_id = int(query.data.replace('settle_full_', ''))
        user_id = cf.get_user(update.effective_user.id).id

        success, message = cf.settle_balance(user_id, target_id)

        if success:
            await query.message.reply_text(f"✅ {message}")
            # TODO: Send notification to creditor
        else:
            await query.message.reply_text(f"❌ {message}")

        context.user_data.clear()
        return ConversationHandler.END

    elif query.data.startswith('settle_partial_'):
        target_id = int(query.data.replace('settle_partial_', ''))
        context.user_data['settle_target_id'] = target_id

        target = cf.get_user_by_internal_id(target_id)
        balances = cf.get_user_balances(cf.get_user(update.effective_user.id).id)
        debt = None
        for b in balances:
            if b['user_id'] == target_id:
                debt = abs(b['amount'])
                break

        if debt is None or debt <= 0:
            await query.message.reply_text("❌ Нет долга для погашения")
            return ConversationHandler.END

        await query.message.reply_text(
            f"💵 Частичное погашение\n\n"
            f"Вы должны {target.first_name}: {debt:.2f} ₽\n\n"
            "Введите сумму погашения:"
        )
        return STATE_PARTIAL_AMOUNT


async def settle_partial_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process partial settlement amount"""
    try:
        amount = float(update.message.text.replace(',', '.'))
        target_id = context.user_data.get('settle_target_id')

        if not target_id:
            await update.message.reply_text("❌ Ошибка: выберите должника снова")
            return await show_main_menu(update, context)

        user_id = cf.get_user(update.effective_user.id).id

        balances = cf.get_user_balances(user_id)
        debt = None
        for b in balances:
            if b['user_id'] == target_id:
                debt = abs(b['amount'])
                break

        if debt is None or debt <= 0:
            await update.message.reply_text("❌ Нет долга для погашения")
            return await show_main_menu(update, context)

        if amount > debt:
            await update.message.reply_text(
                f"❌ Сумма ({amount:.2f}) больше долга ({debt:.2f} ₽)\n"
                f"Введите сумму ≤ {debt:.2f}:"
            )
            return STATE_PARTIAL_AMOUNT

        if amount <= 0:
            await update.message.reply_text(
                "❌ Сумма должна быть больше 0\n"
                "Введите сумму погашения:"
            )
            return STATE_PARTIAL_AMOUNT

        success, message = cf.settle_balance(user_id, target_id, amount)

        if success:
            await update.message.reply_text(f"✅ {message}")
            # TODO: Send notification to creditor
        else:
            await update.message.reply_text(f"❌ {message}")
    except ValueError:
        await update.message.reply_text(
            "❌ Введите число, например: 50\n"
            "Попробуйте ещё раз:"
        )
        return STATE_PARTIAL_AMOUNT

    context.user_data.clear()
    return await show_main_menu(update, context)


# ==================== LINK ACCOUNT ====================

async def link_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show link code for web account linking"""
    query = update.callback_query
    await query.answer()

    user = cf.get_user(update.effective_user.id)
    if not user:
        await query.message.reply_text("❌ Пользователь не найден")
        return

    if user.email:
        await query.message.reply_text(
            f"✅ Ваш аккаунт уже привязан!\n\n"
            f"📧 Email: {user.email}\n"
            f"👤 Имя: {user.first_name}"
        )
    else:
        # This is a Telegram-only user
        await query.message.reply_text(
            "🔗 *Привязка аккаунта*\n\n"
            "Чтобы привязать веб-аккаунт:\n"
            "1. Зарегистрируйтесь на сайте\n"
            "2. Сгенерируйте код в профиле\n"
            "3. Отправьте код сюда\n\n"
            "Или просто используйте бота — всё работает!",
            parse_mode=None
        )

    return await show_main_menu(update, context)


# ==================== BUTTON HANDLER ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard buttons"""
    query = update.callback_query
    await query.answer()

    if query.data == 'add_expense':
        return None
    elif query.data == 'groups_menu':
        return await groups_menu_callback(update, context)
    elif query.data == 'create_group':
        return None
    elif query.data.startswith('view_group_'):
        return None
    elif query.data.startswith('group_expenses_'):
        return None
    elif query.data.startswith('leave_group_'):
        return None
    elif query.data == 'add_user':
        return None
    elif query.data.startswith('expense_group_'):
        return None
    elif query.data.startswith('payer_'):
        return None
    elif query.data.startswith('cat_'):
        return None
    elif query.data.startswith('split_'):
        return None
    elif query.data.startswith('part_toggle_'):
        return None
    elif query.data == 'add_expense_confirm':
        return None
    elif query.data == 'balances':
        return await show_balances(update, context)
    elif query.data == 'settle':
        return None
    elif query.data.startswith('settle_full_') or query.data.startswith('settle_partial_'):
        return None
    elif query.data == 'history':
        return None
    elif query.data == 'link_account':
        return None
    elif query.data == 'back_to_menu':
        return await show_main_menu(update, context)


def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("groups", groups_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("optimize", optimize_command))
    application.add_handler(CommandHandler("support", support))

    # Expense conversation
    expense_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_expense_menu, pattern='^add_expense$')],
        states={
            STATE_SELECT_EXPENSE_GROUP: [CallbackQueryHandler(select_expense_group, pattern='^expense_group_')],
            STATE_SELECT_PAYER: [CallbackQueryHandler(select_payer, pattern='^payer_')],
            STATE_EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            STATE_EXPENSE_DESCRIPTION: [MessageHandler(filters.TEXT, enter_description)],
            STATE_EXPENSE_CATEGORY: [CallbackQueryHandler(select_category, pattern='^cat_')],
            STATE_EXPENSE_SPLIT_TYPE: [CallbackQueryHandler(select_split_type, pattern='^split_')],
            STATE_EXPENSE_PARTICIPANTS: [
                CallbackQueryHandler(toggle_participant, pattern='^part_toggle_'),
                CallbackQueryHandler(confirm_expense, pattern='^add_expense_confirm$'),
            ],
        },
        fallbacks=[]
    )
    application.add_handler(expense_handler)

    # Settle handler
    settle_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(settle_menu, pattern='^settle$')],
        states={
            STATE_SETTLE_TARGET: [CallbackQueryHandler(settle_target_selected, pattern='^settle_(full|partial)_')],
            STATE_PARTIAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, settle_partial_amount)]
        },
        fallbacks=[]
    )
    application.add_handler(settle_handler)

    # Add user handler
    add_user_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_user_menu, pattern='^add_user$')],
        states={
            STATE_ADD_USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_name)]
        },
        fallbacks=[]
    )
    application.add_handler(add_user_handler)

    # Create group handler
    create_group_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_group_start, pattern='^create_group$')],
        states={
            STATE_CREATE_GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_group_name)],
            STATE_CREATE_GROUP_DESC: [MessageHandler(filters.TEXT, create_group_desc)],
        },
        fallbacks=[]
    )
    application.add_handler(create_group_handler)

    # Group view handlers
    application.add_handler(CallbackQueryHandler(view_group, pattern='^view_group_'))
    application.add_handler(CallbackQueryHandler(group_expenses, pattern='^group_expenses_'))
    application.add_handler(CallbackQueryHandler(leave_group, pattern='^leave_group_'))
    application.add_handler(CallbackQueryHandler(groups_menu_callback, pattern='^groups_menu$'))
    application.add_handler(CallbackQueryHandler(link_account, pattern='^link_account$'))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Exception: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ Ошибка. Попробуйте позже.")

    application.add_error_handler(error_handler)

    logger.info("CashFlow bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
