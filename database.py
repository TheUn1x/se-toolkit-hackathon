"""
Database models and configuration for CashFlow
Supports PostgreSQL and SQLite
"""
import logging
import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text,
    Boolean, Enum as SAEnum, Numeric
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from decimal import Decimal
import enum

load_dotenv()

logger = logging.getLogger(__name__)
Base = declarative_base()


# --- Enums ---

class SplitType(str, enum.Enum):
    EQUAL = "equal"
    PERCENT = "percent"
    EXACT = "exact"


class ExpenseCategory(str, enum.Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    HOUSING = "housing"
    ENTERTAINMENT = "entertainment"
    UTILITIES = "utilities"
    GROCERIES = "groceries"
    OTHER = "other"


class Currency(str, enum.Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    KZT = "KZT"
    GBP = "GBP"


# --- ORM Models ---

class User(Base):
    """User account"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    group_memberships = relationship('GroupMember', back_populates='user', cascade='all, delete-orphan')
    expenses_paid = relationship('Expense', back_populates='payer', foreign_keys='Expense.payer_id')
    expense_splits = relationship('ExpenseSplit', back_populates='user', cascade='all, delete-orphan')
    settlements_sent = relationship('Settlement', foreign_keys='Settlement.payer_id', back_populates='payer')
    settlements_received = relationship('Settlement', foreign_keys='Settlement.creditor_id', back_populates='creditor')

    def __repr__(self):
        return f"<User(id={self.id}, name={self.first_name})>"


class Group(Base):
    """Group for shared expenses"""
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship('User', foreign_keys=[created_by])
    members = relationship('GroupMember', back_populates='group', cascade='all, delete-orphan')
    expenses = relationship('Expense', back_populates='group', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Group(id={self.id}, name={self.name})>"


class GroupMember(Base):
    """Membership in a group"""
    __tablename__ = 'group_members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    group = relationship('Group', back_populates='members')
    user = relationship('User', back_populates='group_memberships')

    __table_args__ = (
        # Unique constraint: user can only be in a group once
        # (SQLite needs it via UniqueConstraint, not unique=True on columns)
    )

    def __repr__(self):
        return f"<GroupMember(group={self.group_id}, user={self.user_id})>"


class Expense(Base):
    """An expense record"""
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    payer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='RUB')
    description = Column(String(500), nullable=True)
    category = Column(String(50), default='other')
    split_type = Column(String(20), default='equal')  # equal, percent, exact
    expense_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship('Group', back_populates='expenses')
    payer = relationship('User', foreign_keys=[payer_id], back_populates='expenses_paid')
    splits = relationship('ExpenseSplit', back_populates='expense', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Expense(id={self.id}, amount={self.amount}, payer={self.payer_id})>"


class ExpenseSplit(Base):
    """How an expense is split among participants"""
    __tablename__ = 'expense_splits'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_id = Column(Integer, ForeignKey('expenses.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    share = Column(Float, nullable=False)  # The amount this user owes for this expense

    expense = relationship('Expense', back_populates='splits')
    user = relationship('User', back_populates='expense_splits')

    def __repr__(self):
        return f"<ExpenseSplit(expense={self.expense_id}, user={self.user_id}, share={self.share})>"


class Settlement(Base):
    """A settlement (debt payment) between two users"""
    __tablename__ = 'settlements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    payer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    creditor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='RUB')
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    payer = relationship('User', foreign_keys=[payer_id], back_populates='settlements_sent')
    creditor = relationship('User', foreign_keys=[creditor_id], back_populates='settlements_received')
    group = relationship('Group')

    def __repr__(self):
        return f"<Settlement(payer={self.payer_id}, creditor={self.creditor_id}, amount={self.amount})>"


class TelegramLinkCode(Base):
    """Codes for linking Telegram accounts to web accounts"""
    __tablename__ = 'telegram_link_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User')

    def __repr__(self):
        return f"<TelegramLinkCode(code={self.code}, user={self.user_id})>"


class UserSettings(Base):
    """User notification and preference settings"""
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    notify_expense_added = Column(Boolean, default=True)
    notify_settlement = Column(Boolean, default=True)
    notify_weekly_digest = Column(Boolean, default=True)
    notify_overdue = Column(Boolean, default=True)
    default_currency = Column(String(10), default='RUB')

    user = relationship('User')

    def __repr__(self):
        return f"<UserSettings(user={self.user_id})>"


# --- Database Manager ---

class DatabaseManager:
    """Manages database connection and initialization"""

    def __init__(self, database_url=None, engine=None):
        if engine is not None:
            self.engine = engine
        elif database_url is None:
            database_url = os.getenv(
                'DATABASE_URL',
                'postgresql://postgres:postgres@localhost:5432/cashflow'
            )
            self.engine = self._create_engine(database_url)
        else:
            self.engine = self._create_engine(database_url)

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _create_engine(self, database_url):
        if database_url.startswith('postgresql'):
            return create_engine(
                database_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True
            )
        else:
            if ':memory:' in database_url:
                return create_engine(
                    database_url,
                    echo=False,
                    connect_args={'check_same_thread': False},
                    poolclass=__import__('sqlalchemy.pool', fromlist=['StaticPool']).StaticPool
                )
            return create_engine(
                database_url,
                echo=False,
                connect_args={'check_same_thread': False}
            )

    def get_session(self):
        return self.Session()


class Database:
    """Database manager - backward compatible wrapper"""

    def __init__(self, db_path='cashflow.db'):
        use_sqlite = os.getenv('USE_SQLITE', 'false').lower() == 'true'

        if use_sqlite:
            database_url = f'sqlite:///{db_path}'
            logger.info(f"Using SQLite database: {db_path}")
        else:
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                logger.info(f"Using PostgreSQL database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
            else:
                database_url = f'sqlite:///{db_path}'
                logger.info(f"Using SQLite database (fallback): {db_path}")

        self.db_manager = DatabaseManager(database_url)

    def get_session(self):
        return self.db_manager.get_session()

    def create_user(self, telegram_id=None, first_name=None, username=None, last_name=None, email=None, password_hash=None):
        session = self.get_session()
        try:
            # Check by telegram_id if provided
            if telegram_id:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                if user:
                    return user
            # Check by email if provided
            if email:
                user = session.query(User).filter_by(email=email).first()
                if user:
                    return user
            # Check by username if provided
            if username:
                user = session.query(User).filter_by(username=username).first()
                if user:
                    return user

            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name or "User",
                last_name=last_name,
                email=email,
                password_hash=password_hash,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_user_by_telegram(self, telegram_id):
        session = self.get_session()
        try:
            return session.query(User).filter_by(telegram_id=telegram_id).first()
        finally:
            session.close()

    def get_user_by_id(self, user_id):
        session = self.get_session()
        try:
            return session.query(User).filter_by(id=user_id).first()
        finally:
            session.close()

    def get_user_by_email(self, email):
        session = self.get_session()
        try:
            return session.query(User).filter_by(email=email).first()
        finally:
            session.close()

    def get_user_by_username(self, username):
        session = self.get_session()
        try:
            return session.query(User).filter_by(username=username).first()
        finally:
            session.close()

    def update_balance(self, user_id, amount):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.balance += amount
                session.commit()
                return user
            return None
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def find_user_by_search(self, search_term):
        session = self.get_session()
        try:
            try:
                user = session.query(User).filter_by(telegram_id=int(search_term)).first()
                if user:
                    return user
            except (ValueError, TypeError):
                pass

            user = session.query(User).filter_by(username=search_term).first()
            if user:
                return user

            try:
                user = session.query(User).filter_by(id=int(search_term)).first()
                if user:
                    return user
            except (ValueError, TypeError):
                pass

            return None
        except Exception as e:
            logger.error(f"Error in find_user_by_search: {e}")
            return None
        finally:
            session.close()
