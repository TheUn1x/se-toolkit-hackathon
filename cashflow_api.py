"""
CashFlow API - Complete shared expense tracking business logic
Supports: groups, categories, split types, settlements, optimized debt calculation
"""
from database import (
    Database, User, Group, GroupMember, Expense, ExpenseSplit, Settlement,
    TelegramLinkCode, UserSettings, SplitType, ExpenseCategory, Currency
)
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
import logging
from sqlalchemy import text, and_, or_
from sqlalchemy.orm import joinedload
import random
import string
import math

logger = logging.getLogger(__name__)


def round_money(value: float) -> float:
    """Round to 2 decimal places without losing precision"""
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def distribute_remainder(total: float, shares: List[float]) -> List[float]:
    """
    Distribute rounding remainder so that sum(shares) == total.
    Uses largest remainder method.
    """
    rounded = [round_money(s) for s in shares]
    diff = round_money(total) - sum(rounded)

    if abs(diff) < 0.005:
        return rounded

    # Calculate remainders (the fractional parts that were rounded away)
    remainders = []
    for i, (s, r) in enumerate(zip(shares, rounded)):
        remainders.append((i, s - r))

    # Sort by remainder descending
    remainders.sort(key=lambda x: x[1], reverse=True)

    # Distribute the diff (in kopecks)
    diff_kopecks = int(round(diff * 100))
    idx = 0
    while diff_kopecks != 0:
        if diff_kopecks > 0:
            rounded[remainders[idx][0]] += 0.01
            diff_kopecks -= 1
        else:
            rounded[remainders[idx][0]] -= 0.01
            diff_kopecks += 1
        idx = (idx + 1) % len(remainders)

    return rounded


class CashFlowAPI:
    """Complete CashFlow business logic"""

    def __init__(self, db_path='cashflow.db'):
        self.db = Database(db_path)
        self._init_tables()

    def _init_tables(self):
        """Create all tables, migrate old schema if needed"""
        session = self.db.get_session()
        try:
            # Detect database type
            is_postgres = self.db.db_manager.engine.url.drivername.startswith('postgresql')

            if is_postgres:
                # For PostgreSQL, just use ORM create_all — no migration from old schema needed
                # (old MyBank schema was SQLite-only)
                from database import Base
                Base.metadata.create_all(self.db.db_manager.engine)
                session.commit()
                session.close()
                return

            # SQLite: check if old expenses table exists (with 'participants' column instead of new schema)
            old_table_check = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'"
            )).fetchone()

            if old_table_check:
                # Check if it has the old 'participants' column
                columns = session.execute(text("PRAGMA table_info(expenses)")).fetchall()
                col_names = [c[1] for c in columns]
                if 'participants' in col_names and 'group_id' not in col_names:
                    # Migrate old schema
                    logger.info("Migrating old expenses table schema...")
                    session.execute(text("DROP TABLE IF EXISTS expenses"))
                    session.execute(text("DROP TABLE IF EXISTS expense_splits"))
                    session.execute(text("DROP TABLE IF EXISTS settlements"))
                    session.execute(text("DROP TABLE IF EXISTS groups"))
                    session.execute(text("DROP TABLE IF EXISTS group_members"))
                    session.execute(text("DROP TABLE IF EXISTS telegram_link_codes"))
                    session.execute(text("DROP TABLE IF EXISTS user_settings"))
                    session.commit()

            session.execute(text("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    created_by INTEGER NOT NULL,
                    is_archived BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """))

            session.execute(text("""
                CREATE TABLE IF NOT EXISTS group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES groups(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))

            session.execute(text("""
                CREATE TABLE IF NOT EXISTS group_members_unique (
                    group_id INTEGER,
                    user_id INTEGER
                )
            """))

            session.execute(text("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER,
                    payer_id INTEGER NOT NULL,
                    amount FLOAT NOT NULL,
                    currency VARCHAR(10) DEFAULT 'RUB',
                    description VARCHAR(500),
                    category VARCHAR(50) DEFAULT 'other',
                    split_type VARCHAR(20) DEFAULT 'equal',
                    expense_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES groups(id),
                    FOREIGN KEY (payer_id) REFERENCES users(id)
                )
            """))

            session.execute(text("""
                CREATE TABLE IF NOT EXISTS expense_splits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    share FLOAT NOT NULL,
                    FOREIGN KEY (expense_id) REFERENCES expenses(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))

            session.execute(text("""
                CREATE TABLE IF NOT EXISTS settlements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payer_id INTEGER NOT NULL,
                    creditor_id INTEGER NOT NULL,
                    amount FLOAT NOT NULL,
                    currency VARCHAR(10) DEFAULT 'RUB',
                    group_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (payer_id) REFERENCES users(id),
                    FOREIGN KEY (creditor_id) REFERENCES users(id),
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                )
            """))

            session.execute(text("""
                CREATE TABLE IF NOT EXISTS telegram_link_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    expires_at DATETIME NOT NULL,
                    used BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))

            session.execute(text("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    notify_expense_added BOOLEAN DEFAULT 1,
                    notify_settlement BOOLEAN DEFAULT 1,
                    notify_weekly_digest BOOLEAN DEFAULT 1,
                    notify_overdue BOOLEAN DEFAULT 1,
                    default_currency VARCHAR(10) DEFAULT 'RUB',
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))

            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_expenses_group ON expenses(group_id)",
                "CREATE INDEX IF NOT EXISTS idx_expenses_payer ON expenses(payer_id)",
                "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)",
                "CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date)",
                "CREATE INDEX IF NOT EXISTS idx_splits_expense ON expense_splits(expense_id)",
                "CREATE INDEX IF NOT EXISTS idx_splits_user ON expense_splits(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_settlements_payer ON settlements(payer_id)",
                "CREATE INDEX IF NOT EXISTS idx_settlements_creditor ON settlements(creditor_id)",
                "CREATE INDEX IF NOT EXISTS idx_members_group ON group_members(group_id)",
                "CREATE INDEX IF NOT EXISTS idx_members_user ON group_members(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_link_code ON telegram_link_codes(code)",
            ]
            for idx_sql in indexes:
                session.execute(text(idx_sql))

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating tables: {e}")
            raise
        finally:
            session.close()

    # ==================== USER MANAGEMENT ====================

    def register_user(self, telegram_id: int = None, first_name: str = None,
                      username: str = None, last_name: str = None,
                      email: str = None, password_hash: str = None) -> User:
        return self.db.create_user(
            telegram_id=telegram_id, first_name=first_name,
            username=username, last_name=last_name,
            email=email, password_hash=password_hash
        )

    def register_pending_user(self, username: str) -> User:
        session = self.db.get_session()
        try:
            existing = session.query(User).filter_by(username=username).first()
            if existing:
                return existing

            user = User(
                telegram_id=0,
                username=username,
                first_name=username,
                last_name=None,
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            # Create default settings
            settings = UserSettings(user_id=user.id)
            session.add(settings)
            session.commit()
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error registering pending user: {e}")
            raise
        finally:
            session.close()

    def activate_pending_user(self, username: str, telegram_id: int, first_name: str) -> Optional[User]:
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(username=username, telegram_id=0).first()
            if user:
                user.telegram_id = telegram_id
                user.first_name = first_name
                session.commit()

                # Ensure settings exist
                settings = session.query(UserSettings).filter_by(user_id=user.id).first()
                if not settings:
                    session.add(UserSettings(user_id=user.id))
                    session.commit()

                return user
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"Error activating pending user: {e}")
            return None
        finally:
            session.close()

    def get_user(self, telegram_id: int) -> Optional[User]:
        return self.db.get_user_by_telegram(telegram_id)

    def get_user_by_internal_id(self, user_id: int) -> Optional[User]:
        return self.db.get_user_by_id(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.get_user_by_username(username)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.get_user_by_email(email)

    def get_all_users(self) -> List[User]:
        session = self.db.get_session()
        try:
            return session.query(User).all()
        finally:
            session.close()

    def get_user_count(self) -> int:
        session = self.db.get_session()
        try:
            return session.query(User).count()
        finally:
            session.close()

    def set_password(self, user_id: int, password_hash: str) -> bool:
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.password_hash = password_hash
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def get_or_create_settings(self, user_id: int) -> UserSettings:
        session = self.db.get_session()
        try:
            settings = session.query(UserSettings).filter_by(user_id=user_id).first()
            if not settings:
                settings = UserSettings(user_id=user_id)
                session.add(settings)
                session.commit()
                session.refresh(settings)
            return settings
        finally:
            session.close()

    # ==================== TELEGRAM LINK CODES ====================

    def generate_link_code(self, user_id: int) -> Optional[str]:
        """Generate a unique code for linking Telegram account"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return None

            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            expires_at = datetime.utcnow() + timedelta(hours=24)

            link_code = TelegramLinkCode(
                user_id=user_id,
                code=code,
                expires_at=expires_at,
            )
            session.add(link_code)
            session.commit()
            return code
        except Exception as e:
            session.rollback()
            logger.error(f"Error generating link code: {e}")
            return None
        finally:
            session.close()

    def consume_link_code(self, code: str, telegram_id: int, first_name: str) -> Optional[User]:
        """Consume a link code to link Telegram account"""
        session = self.db.get_session()
        try:
            link = session.query(TelegramLinkCode).filter_by(code=code, used=False).first()
            if not link:
                return None
            if link.expires_at < datetime.utcnow():
                return None

            user = session.query(User).filter_by(id=link.user_id).first()
            if not user:
                return None

            user.telegram_id = telegram_id
            if user.first_name == user.username or not user.first_name:
                user.first_name = first_name
            link.used = True

            # Ensure settings
            settings = session.query(UserSettings).filter_by(user_id=user.id).first()
            if not settings:
                session.add(UserSettings(user_id=user.id))

            session.commit()
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error consuming link code: {e}")
            return None
        finally:
            session.close()

    # ==================== GROUPS ====================

    def create_group(self, name: str, creator_id: int, description: str = None) -> Optional[Group]:
        """Create a group and add creator as member"""
        session = self.db.get_session()
        try:
            group = Group(
                name=name,
                description=description,
                created_by=creator_id,
            )
            session.add(group)
            session.flush()

            # Add creator as member
            member = GroupMember(group_id=group.id, user_id=creator_id)
            session.add(member)
            session.commit()
            session.refresh(group)
            return group
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating group: {e}")
            return None
        finally:
            session.close()

    def get_group(self, group_id: int) -> Optional[Group]:
        session = self.db.get_session()
        try:
            return session.query(Group).options(
                joinedload(Group.members).joinedload(GroupMember.user)
            ).filter_by(id=group_id).first()
        finally:
            session.close()

    def get_user_groups(self, user_id: int, include_archived: bool = False) -> List[Group]:
        session = self.db.get_session()
        try:
            query = (
                session.query(Group)
                .join(GroupMember, Group.id == GroupMember.group_id)
                .filter(GroupMember.user_id == user_id)
            )
            if not include_archived:
                query = query.filter(Group.is_archived == False)
            return query.all()
        finally:
            session.close()

    def get_group_members(self, group_id: int) -> List[User]:
        session = self.db.get_session()
        try:
            members = session.query(GroupMember).filter_by(group_id=group_id).all()
            return [m.user for m in members if m.user]
        finally:
            session.close()

    def add_group_member(self, group_id: int, user_id: int) -> Tuple[bool, str]:
        """Add a user to a group"""
        session = self.db.get_session()
        try:
            # Check if already member
            existing = session.query(GroupMember).filter_by(
                group_id=group_id, user_id=user_id
            ).first()
            if existing:
                return False, "Пользователь уже в группе"

            group = session.query(Group).filter_by(id=group_id).first()
            if not group:
                return False, "Группа не найдена"
            if group.is_archived:
                return False, "Нельзя加入 в архивированную группу"

            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False, "Пользователь не найден"

            member = GroupMember(group_id=group_id, user_id=user_id)
            session.add(member)
            session.commit()
            return True, "Участник добавлен"
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding group member: {e}")
            return False, str(e)
        finally:
            session.close()

    def remove_group_member(self, group_id: int, user_id: int) -> Tuple[bool, str]:
        """Remove user from group. Check for open balances first."""
        session = self.db.get_session()
        try:
            member = session.query(GroupMember).filter_by(
                group_id=group_id, user_id=user_id
            ).first()
            if not member:
                return False, "Пользователь не в группе"

            # Check for open balances in this group
            balances = self._get_group_balances_internal(session, group_id)
            user_has_debt = False
            for b in balances:
                if (b.get('debtor_id') == user_id or b.get('creditor_id') == user_id) and abs(b['amount']) > 0.01:
                    user_has_debt = True
                    break

            if user_has_debt:
                return False, "Нельзя покинуть группу с открытым балансом. Сначала погасите долги."

            session.delete(member)

            # If group has no more members, archive it
            remaining = session.query(GroupMember).filter_by(group_id=group_id).count()
            if remaining == 0:
                group = session.query(Group).filter_by(id=group_id).first()
                if group:
                    group.is_archived = True

            session.commit()
            return True, "Вы покинули группу"
        except Exception as e:
            session.rollback()
            logger.error(f"Error removing group member: {e}")
            return False, str(e)
        finally:
            session.close()

    def archive_group(self, group_id: int, user_id: int) -> Tuple[bool, str]:
        """Archive a group (only creator can)"""
        session = self.db.get_session()
        try:
            group = session.query(Group).filter_by(id=group_id).first()
            if not group:
                return False, "Группа не найдена"
            if group.created_by != user_id:
                return False, "Только создатель может архивировать группу"

            # Check for open balances
            balances = self._get_group_balances_internal(session, group_id)
            has_open = any(abs(b['amount']) > 0.01 for b in balances)
            if has_open:
                return False, "Нельзя архивировать группу с открытыми балансами"

            group.is_archived = True
            session.commit()
            return True, "Группа архивирована"
        except Exception as e:
            session.rollback()
            logger.error(f"Error archiving group: {e}")
            return False, str(e)
        finally:
            session.close()

    # ==================== EXPENSES ====================

    def add_expense(
        self,
        payer_id: int,
        amount: float,
        participant_ids: List[int] = None,  # Backward compat: was 3rd positional
        description: str = None,
        category: str = 'other',
        currency: str = 'RUB',
        split_type: str = 'equal',
        shares: Dict[int, float] = None,
        group_id: int = None,
        expense_date: datetime = None,
    ) -> Tuple[Optional[Expense], str]:
        """
        Add a shared expense.

        split_type: 'equal', 'percent', 'exact'
        participant_ids: list of user IDs to split with (excluding payer)
        shares: for 'percent' and 'exact' - dict of {user_id: share}
                for 'percent': share is a percentage (e.g., 50 means 50%)
                for 'exact': share is the exact amount owed

        Returns: (expense, error_message)
        """
        session = self.db.get_session()
        try:
            # Validation
            if amount <= 0:
                return None, "Сумма должна быть больше 0"

            if participant_ids is None:
                participant_ids = []

            # Remove payer from participants if accidentally included
            participant_ids = [p for p in participant_ids if p != payer_id]

            # For equal split, we need at least one participant
            if not participant_ids and split_type == 'equal':
                return None, "Нужен хотя бы один участник кроме плательщика"

            # For exact/percent, validate shares
            if split_type in ('percent', 'exact') and shares:
                if set(shares.keys()) != set(participant_ids):
                    return None, "Доли должны совпадать с участниками"

            # If group is specified, verify payer is a member
            if group_id:
                group = session.query(Group).filter_by(id=group_id).first()
                if not group or group.is_archived:
                    return None, "Группа не найдена или архивирована"
                is_member = session.query(GroupMember).filter_by(
                    group_id=group_id, user_id=payer_id
                ).first()
                if not is_member:
                    return None, "Плательщик не в группе"

                # Verify all participants are in the group
                for pid in participant_ids:
                    if not session.query(GroupMember).filter_by(
                        group_id=group_id, user_id=pid
                    ).first():
                        return None, f"Пользователь {pid} не в группе"

            # Create expense
            expense = Expense(
                payer_id=payer_id,
                amount=amount,
                currency=currency,
                description=description,
                category=category,
                split_type=split_type,
                group_id=group_id,
                expense_date=expense_date or datetime.utcnow(),
            )
            session.add(expense)
            session.flush()

            # Calculate and create splits
            if split_type == 'equal':
                self._create_equal_splits(session, expense, payer_id, participant_ids, amount)
            elif split_type == 'percent':
                self._create_percent_splits(session, expense, participant_ids, shares, amount)
            elif split_type == 'exact':
                self._create_exact_splits(session, expense, participant_ids, shares, amount)
            else:
                return None, "Неизвестный тип деления"

            session.commit()
            session.refresh(expense)

            # Reload with splits
            expense = session.query(Expense).options(
                joinedload(Expense.splits).joinedload(ExpenseSplit.user)
            ).filter_by(id=expense.id).first()

            return expense, ""
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding expense: {e}")
            return None, str(e)
        finally:
            session.close()

    def _create_equal_splits(self, session, expense, payer_id, participant_ids, amount):
        """Split equally among all participants including payer"""
        all_ids = [payer_id] + participant_ids
        total_people = len(all_ids)
        if total_people == 0:
            return

        per_person = amount / total_people
        # Distribute with rounding
        shares = distribute_remainder(amount, [per_person] * total_people)

        for i, uid in enumerate(all_ids):
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=uid,
                share=shares[i],
            )
            session.add(split)

    def _create_percent_splits(self, session, expense, participant_ids, shares, amount):
        """Split by percentages. Payer's share is (100% - sum of others)%.

        shares: dict of {user_id: percent} for participants only.
        If shares is None/empty, falls back to equal split.
        """
        # If no shares provided, fall back to equal split
        if not shares:
            self._create_equal_splits(session, expense, expense.payer_id, participant_ids, amount)
            return

        total_percent = sum(shares.values())
        payer_percent = 100.0 - total_percent

        if payer_percent < 0:
            raise ValueError("Сумма процентов не может превышать 100%")

        all_ids = list(participant_ids) + [expense.payer_id]
        raw_amounts = []

        for uid in participant_ids:
            pct = shares.get(uid, 0)
            raw_amounts.append(amount * pct / 100.0)

        raw_amounts.append(amount * payer_percent / 100.0)

        final_amounts = distribute_remainder(amount, raw_amounts)

        for i, uid in enumerate(all_ids):
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=uid,
                share=final_amounts[i],
            )
            session.add(split)

    def _create_exact_splits(self, session, expense, participant_ids, shares, amount):
        """Split by exact amounts. Payer's share = total - sum(participant_shares).

        shares: dict of {user_id: exact_amount} for participants only.
        If shares is None/empty, falls back to equal split.
        """
        # If no shares provided, fall back to equal split
        if not shares:
            self._create_equal_splits(session, expense, expense.payer_id, participant_ids, amount)
            return

        total_participant_shares = sum(shares.values())
        payer_share = amount - total_participant_shares

        if payer_share < -0.01:
            raise ValueError("Сумма долей участников превышает общую сумму")

        payer_share = max(0, payer_share)  # Cap at 0 minimum

        all_ids = list(participant_ids) + [expense.payer_id]
        raw_amounts = [shares.get(uid, 0) for uid in participant_ids] + [payer_share]

        # For exact splits, we trust the user's amounts but still round properly
        final_amounts = distribute_remainder(amount, raw_amounts)

        for i, uid in enumerate(all_ids):
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=uid,
                share=final_amounts[i],
            )
            session.add(split)

    def get_expense(self, expense_id: int) -> Optional[Expense]:
        session = self.db.get_session()
        try:
            return session.query(Expense).options(
                joinedload(Expense.splits).joinedload(ExpenseSplit.user),
                joinedload(Expense.payer)
            ).filter_by(id=expense_id).first()
        finally:
            session.close()

    def get_user_expenses(self, user_id: int, limit: int = 50,
                          group_id: int = None, category: str = None,
                          date_from: datetime = None, date_to: datetime = None) -> List[Expense]:
        """Get expenses where user is involved (as payer or participant)"""
        session = self.db.get_session()
        try:
            query = (
                session.query(Expense)
                .options(
                    joinedload(Expense.splits).joinedload(ExpenseSplit.user),
                    joinedload(Expense.payer)
                )
                .filter(
                    or_(
                        Expense.payer_id == user_id,
                        Expense.id.in_(
                            session.query(ExpenseSplit.expense_id).filter(ExpenseSplit.user_id == user_id)
                        )
                    )
                )
            )

            if group_id:
                query = query.filter(Expense.group_id == group_id)
            if category:
                query = query.filter(Expense.category == category)
            if date_from:
                query = query.filter(Expense.expense_date >= date_from)
            if date_to:
                query = query.filter(Expense.expense_date <= date_to)

            return query.order_by(Expense.expense_date.desc()).limit(limit).all()
        finally:
            session.close()

    def get_group_expenses(self, group_id: int, limit: int = 50,
                           category: str = None,
                           date_from: datetime = None,
                           date_to: datetime = None) -> List[Expense]:
        session = self.db.get_session()
        try:
            query = (
                session.query(Expense)
                .options(
                    joinedload(Expense.splits).joinedload(ExpenseSplit.user),
                    joinedload(Expense.payer)
                )
                .filter_by(group_id=group_id)
            )

            if category:
                query = query.filter(Expense.category == category)
            if date_from:
                query = query.filter(Expense.expense_date >= date_from)
            if date_to:
                query = query.filter(Expense.expense_date <= date_to)

            return query.order_by(Expense.expense_date.desc()).limit(limit).all()
        finally:
            session.close()

    def get_all_expenses(self, limit: int = 50) -> List[Expense]:
        session = self.db.get_session()
        try:
            return session.query(Expense).options(
                joinedload(Expense.splits),
                joinedload(Expense.payer)
            ).order_by(Expense.expense_date.desc()).limit(limit).all()
        finally:
            session.close()

    def edit_expense(self, expense_id: int, amount: float = None,
                     description: str = None, category: str = None,
                     split_type: str = None, participant_ids: List[int] = None,
                     shares: Dict[int, float] = None,
                     expense_date: datetime = None) -> Tuple[bool, str]:
        """Edit an existing expense"""
        session = self.db.get_session()
        try:
            expense = session.query(Expense).filter_by(id=expense_id).first()
            if not expense:
                return False, "Трата не найдена"

            # Check if there are settlements against this expense
            has_settlements = session.query(Settlement).filter_by().first()  # settlements are pairwise, not per-expense
            # We can't easily check if specific expense has settlements since settlements are pairwise
            # But we can warn if any settlements exist at all involving the payer
            # For now, allow editing but note that the user should be careful

            if amount is not None:
                if amount <= 0:
                    return False, "Сумма должна быть больше 0"
                expense.amount = amount

            if description is not None:
                expense.description = description
            if category is not None:
                expense.category = category
            if split_type is not None:
                expense.split_type = split_type
            if expense_date is not None:
                expense.expense_date = expense_date

            # Recalculate splits if participants or split_type changed
            if participant_ids is not None or split_type is not None or shares is not None:
                # Delete old splits
                session.query(ExpenseSplit).filter_by(expense_id=expense_id).delete()

                if participant_ids is None:
                    participant_ids = []

                participant_ids = [p for p in participant_ids if p != expense.payer_id]

                if not participant_ids and expense.split_type == 'equal':
                    return False, "Нужен хотя бы один участник"

                if split_type == 'equal':
                    self._create_equal_splits(session, expense, expense.payer_id, participant_ids, expense.amount)
                elif split_type == 'percent':
                    self._create_percent_splits(session, expense, participant_ids, shares, expense.amount)
                elif split_type == 'exact':
                    self._create_exact_splits(session, expense, participant_ids, shares, expense.amount)

            session.commit()
            return True, "Трата обновлена"
        except Exception as e:
            session.rollback()
            logger.error(f"Error editing expense: {e}")
            return False, str(e)
        finally:
            session.close()

    def delete_expense(self, expense_id: int) -> Tuple[bool, str]:
        """Delete an expense and its splits"""
        session = self.db.get_session()
        try:
            expense = session.query(Expense).filter_by(id=expense_id).first()
            if not expense:
                return False, "Трата не найдена"

            # Check if there are settlements between any of the involved users
            splits = session.query(ExpenseSplit).filter_by(expense_id=expense_id).all()
            involved_ids = set(s.user_id for s in splits)
            involved_ids.add(expense.payer_id)

            # Check if any settlements exist between involved users
            for uid1 in involved_ids:
                for uid2 in involved_ids:
                    if uid1 != uid2:
                        settlement_count = session.query(Settlement).filter(
                            Settlement.payer_id == uid1,
                            Settlement.creditor_id == uid2
                        ).count()
                        if settlement_count > 0:
                            return False, "Нельзя удалить трату: существуют погашения между участниками этой траты. Сначала отмените погашения."

            # Delete splits first
            session.query(ExpenseSplit).filter_by(expense_id=expense_id).delete()
            # Delete expense
            session.delete(expense)
            session.commit()
            return True, "Трата удалена"
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting expense: {e}")
            return False, str(e)
        finally:
            session.close()

    # ==================== BALANCES ====================

    def get_user_balances(self, user_id: int, group_id: int = None) -> List[Dict]:
        """
        Calculate net balance between user_id and every other user.

        amount > 0  →  someone owes user_id (user_id should receive)
        amount < 0  →  user_id owes someone (user_id should pay)

        If group_id is specified, calculate only for that group.
        """
        session = self.db.get_session()
        try:
            all_users = session.query(User).all()
            net_balances = {u.id: 0.0 for u in all_users if u.id != user_id}

            # Get expenses
            expense_query = session.query(Expense).options(
                joinedload(Expense.splits)
            )
            if group_id:
                expense_query = expense_query.filter(Expense.group_id == group_id)

            expenses = expense_query.all()

            for exp in expenses:
                if not exp.splits:
                    continue

                payer_share = None
                participant_shares = {}

                for split in exp.splits:
                    if split.user_id == exp.payer_id:
                        payer_share = split.share
                    else:
                        participant_shares[split.user_id] = split.share

                if payer_share is None:
                    continue

                for other_id in list(net_balances.keys()):
                    if other_id == user_id:
                        continue

                    if exp.payer_id == user_id and other_id in participant_shares:
                        # user_id paid, other_id was a participant → other_id owes user_id
                        net_balances[other_id] += participant_shares[other_id]
                    elif exp.payer_id == other_id and user_id in participant_shares:
                        # other_id paid, user_id was a participant → user_id owes other_id
                        net_balances[other_id] -= participant_shares.get(user_id, 0)

            # Apply settlements
            settlement_query = session.query(Settlement)
            if group_id:
                settlement_query = settlement_query.filter(
                    or_(
                        and_(Settlement.payer_id == user_id, Settlement.group_id == group_id),
                        and_(Settlement.creditor_id == user_id, Settlement.group_id == group_id),
                    )
                )
            else:
                settlement_query = settlement_query.filter(
                    or_(Settlement.payer_id == user_id, Settlement.creditor_id == user_id)
                )

            settlements = settlement_query.all()

            for stl in settlements:
                if stl.payer_id == user_id and stl.creditor_id in net_balances:
                    # user_id paid creditor_id → reduces user_id's debt to creditor_id
                    net_balances[stl.creditor_id] += stl.amount
                elif stl.creditor_id == user_id and stl.payer_id in net_balances:
                    # payer_id paid user_id → reduces payer_id's debt to user_id
                    net_balances[stl.payer_id] -= stl.amount

            result = []
            for uid, amount in net_balances.items():
                rounded = round(amount, 2)
                if abs(rounded) > 0.01:
                    user = session.query(User).filter_by(id=uid).first()
                    result.append({
                        'user_id': uid,
                        'user': user.first_name if user else 'Unknown',
                        'amount': rounded,
                    })

            return sorted(result, key=lambda x: abs(x['amount']), reverse=True)
        except Exception as e:
            logger.error(f"Error calculating balances: {e}")
            return []
        finally:
            session.close()

    def get_group_balances(self, group_id: int) -> List[Dict]:
        """Get all balances within a group (pairwise)"""
        session = self.db.get_session()
        try:
            return self._get_group_balances_internal(session, group_id)
        finally:
            session.close()

    def _get_group_balances_internal(self, session, group_id: int) -> List[Dict]:
        """Internal version that reuses existing session"""
        try:
            members = session.query(GroupMember).filter_by(group_id=group_id).all()
            member_ids = [m.user_id for m in members]

            net_balances = {uid: {oid: 0.0 for oid in member_ids if oid != uid} for uid in member_ids}

            # Expenses in this group
            expenses = session.query(Expense).options(
                joinedload(Expense.splits)
            ).filter_by(group_id=group_id).all()

            for exp in expenses:
                if not exp.splits:
                    continue

                participant_shares = {}
                for split in exp.splits:
                    participant_shares[split.user_id] = split.share

                payer_id = exp.payer_id
                for other_id in member_ids:
                    if other_id == payer_id:
                        continue
                    if other_id in participant_shares:
                        # other_id owes payer_id the share amount
                        if other_id in net_balances and payer_id in net_balances[other_id]:
                            net_balances[other_id][payer_id] += participant_shares[other_id]

            # Settlements in this group
            settlements = session.query(Settlement).filter_by(group_id=group_id).all()
            for stl in settlements:
                if stl.payer_id in net_balances and stl.creditor_id in net_balances[stl.payer_id]:
                    net_balances[stl.payer_id][stl.creditor_id] -= stl.amount

            result = []
            for debtor_id in net_balances:
                for creditor_id, amount in net_balances[debtor_id].items():
                    rounded = round(amount, 2)
                    if abs(rounded) > 0.01:
                        debtor = session.query(User).filter_by(id=debtor_id).first()
                        creditor = session.query(User).filter_by(id=creditor_id).first()
                        result.append({
                            'debtor_id': debtor_id,
                            'debtor_name': debtor.first_name if debtor else 'Unknown',
                            'creditor_id': creditor_id,
                            'creditor_name': creditor.first_name if creditor else 'Unknown',
                            'amount': rounded,
                        })

            return result
        except Exception as e:
            logger.error(f"Error calculating group balances: {e}")
            return []

    def get_user_total_balance(self, user_id: int) -> Dict:
        """Get user's total balance across all groups (owed, owes, net)"""
        balances = self.get_user_balances(user_id)
        total_owed = sum(b['amount'] for b in balances if b['amount'] > 0)
        total_owes = abs(sum(b['amount'] for b in balances if b['amount'] < 0))
        return {
            'total_owed': round(total_owed, 2),
            'total_owes': round(total_owes, 2),
            'net': round(total_owed - total_owes, 2),
        }

    # ==================== OPTIMIZED DEBT SETTLEMENT ====================

    def get_optimized_settlements(self, user_id: int = None, group_id: int = None) -> List[Dict]:
        """
        Calculate the minimum number of transactions to settle all debts.
        Uses a greedy algorithm to minimize transaction count.

        If user_id is specified, return only settlements involving that user.
        If group_id is specified, calculate for that group only.
        """
        session = self.db.get_session()
        try:
            if group_id:
                members = session.query(GroupMember).filter_by(group_id=group_id).all()
                member_ids = [m.user_id for m in members]
            else:
                all_users = session.query(User).all()
                member_ids = [u.id for u in all_users]

            if len(member_ids) < 2:
                return []

            # Calculate net position for each user
            # Positive = should receive money, Negative = should pay money
            net_positions = {uid: 0.0 for uid in member_ids}

            # Get expenses
            expense_query = session.query(Expense).options(joinedload(Expense.splits))
            if group_id:
                expense_query = expense_query.filter(Expense.group_id == group_id)
            expenses = expense_query.all()

            for exp in expenses:
                if not exp.splits:
                    continue
                for split in exp.splits:
                    if split.user_id == exp.payer_id:
                        # Payer is owed their own share back (they already paid)
                        pass
                    else:
                        # This person owes the payer
                        net_positions[split.user_id] -= split.share
                        net_positions[exp.payer_id] += split.share

            # Apply existing settlements
            settlement_query = session.query(Settlement)
            if group_id:
                settlement_query = settlement_query.filter(Settlement.group_id == group_id)
            settlements = settlement_query.all()

            for stl in settlements:
                net_positions[stl.payer_id] += stl.amount
                net_positions[stl.creditor_id] -= stl.amount

            # Separate into debtors (negative) and creditors (positive)
            debtors = []
            creditors = []
            for uid, amount in net_positions.items():
                rounded = round(amount, 2)
                if rounded < -0.01:
                    debtors.append({'user_id': uid, 'amount': rounded})
                elif rounded > 0.01:
                    creditors.append({'user_id': uid, 'amount': rounded})

            # Greedy matching: largest debtor pays largest creditor
            optimized = []
            debtors.sort(key=lambda x: x['amount'])  # most negative first
            creditors.sort(key=lambda x: x['amount'], reverse=True)  # most positive first

            di = 0
            ci = 0
            while di < len(debtors) and ci < len(creditors):
                debtor = debtors[di]
                creditor = creditors[ci]

                # Amount to settle
                pay_amount = min(abs(debtor['amount']), creditor['amount'])
                pay_amount = round_money(pay_amount)

                if pay_amount > 0.01:
                    debtor_user = session.query(User).filter_by(id=debtor['user_id']).first()
                    creditor_user = session.query(User).filter_by(id=creditor['user_id']).first()

                    settlement = {
                        'from_user_id': debtor['user_id'],
                        'from_user_name': debtor_user.first_name if debtor_user else 'Unknown',
                        'to_user_id': creditor['user_id'],
                        'to_user_name': creditor_user.first_name if creditor_user else 'Unknown',
                        'amount': pay_amount,
                    }

                    # Filter if specific user requested
                    if user_id is None or debtor['user_id'] == user_id or creditor['user_id'] == user_id:
                        optimized.append(settlement)

                # Update remaining amounts
                debtor['amount'] += pay_amount
                creditor['amount'] -= pay_amount

                if abs(debtor['amount']) < 0.01:
                    di += 1
                if abs(creditor['amount']) < 0.01:
                    ci += 1

            return optimized
        except Exception as e:
            logger.error(f"Error calculating optimized settlements: {e}")
            return []
        finally:
            session.close()

    # ==================== SETTLEMENTS ====================

    def settle_balance(self, user1_id: int, user2_id: int, amount: float = None,
                       group_id: int = None, currency: str = 'RUB') -> Tuple[bool, str]:
        """
        Settle balance between two users.
        user1 is paying user2.

        If amount is None → full settlement.
        If amount is specified → partial (capped at actual debt).
        """
        session = self.db.get_session()
        try:
            # Calculate what user1 owes user2
            balances = self.get_user_balances(user1_id, group_id=group_id)
            balance_with_user2 = None
            for b in balances:
                if b['user_id'] == user2_id:
                    balance_with_user2 = b['amount']
                    break

            # Negative balance = user1 owes user2
            if balance_with_user2 is None or balance_with_user2 >= 0:
                return False, "Нет долга для погашения"

            debt_amount = abs(balance_with_user2)

            if amount is None:
                settle_amount = debt_amount
            else:
                settle_amount = min(round_money(amount), debt_amount)

            if settle_amount <= 0:
                return False, "Сумма должна быть больше 0"

            # Record settlement
            settlement = Settlement(
                payer_id=user1_id,
                creditor_id=user2_id,
                amount=settle_amount,
                currency=currency,
                group_id=group_id,
            )
            session.add(settlement)
            session.commit()

            remaining = debt_amount - settle_amount

            if amount is None or remaining < 0.01:
                return True, f"Долг погашен полностью: {settle_amount:.2f} ₽"
            else:
                return True, f"Погашено: {settle_amount:.2f} ₽ (осталось: {remaining:.2f} ₽)"
        except Exception as e:
            session.rollback()
            logger.error(f"Error settling balance: {e}")
            return False, str(e)
        finally:
            session.close()

    def get_settlement_history(self, user_id: int = None, group_id: int = None,
                                limit: int = 50) -> List[Settlement]:
        """Get settlement history"""
        session = self.db.get_session()
        try:
            query = session.query(Settlement)
            if user_id:
                query = query.filter(
                    or_(Settlement.payer_id == user_id, Settlement.creditor_id == user_id)
                )
            if group_id:
                query = query.filter(Settlement.group_id == group_id)

            return query.order_by(Settlement.created_at.desc()).limit(limit).all()
        finally:
            session.close()

    # ==================== NOTIFICATIONS (data queries) ====================

    def get_users_with_overdue_debts(self, days: int = 7) -> List[Dict]:
        """Get users who have debts older than N days"""
        session = self.db.get_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            # Find users who have open balances and haven't settled in a while
            users = session.query(User).all()
            result = []

            for user in users:
                balances = self.get_user_balances(user.id)
                owes = [b for b in balances if b['amount'] < 0]
                if owes:
                    # Check their last settlement
                    last_settlement = session.query(Settlement).filter(
                        or_(Settlement.payer_id == user.id, Settlement.creditor_id == user.id)
                    ).order_by(Settlement.created_at.desc()).first()

                    if not last_settlement or last_settlement.created_at < cutoff:
                        result.append({
                            'user_id': user.id,
                            'telegram_id': user.telegram_id,
                            'name': user.first_name,
                            'owes': owes,
                        })

            return result
        except Exception as e:
            logger.error(f"Error getting overdue debts: {e}")
            return []
        finally:
            session.close()

    def get_weekly_digest(self, user_id: int) -> Dict:
        """Get weekly digest for a user"""
        week_ago = datetime.utcnow() - timedelta(days=7)

        balances = self.get_user_balances(user_id)
        recent_expenses = self.get_user_expenses(user_id, limit=20, date_from=week_ago)
        recent_settlements = self.get_settlement_history(user_id=user_id, limit=20)

        user = self.get_user_by_internal_id(user_id)

        return {
            'user_id': user_id,
            'user_name': user.first_name if user else 'Unknown',
            'balances': balances,
            'total_owed': round(sum(b['amount'] for b in balances if b['amount'] > 0), 2),
            'total_owes': round(abs(sum(b['amount'] for b in balances if b['amount'] < 0)), 2),
            'recent_expenses': [
                {
                    'id': e.id,
                    'description': e.description,
                    'amount': e.amount,
                    'date': str(e.expense_date),
                }
                for e in recent_expenses[:10]
            ],
            'recent_settlements': [
                {
                    'amount': s.amount,
                    'date': str(s.created_at),
                }
                for s in recent_settlements[:10]
            ],
        }

    # ==================== CATEGORIES ====================

    @staticmethod
    def get_categories() -> List[Dict]:
        return [
            {'value': c.value, 'label': c.name.replace('_', ' ').title()}
            for c in ExpenseCategory
        ]

    @staticmethod
    def get_currencies() -> List[str]:
        return [c.value for c in Currency]
