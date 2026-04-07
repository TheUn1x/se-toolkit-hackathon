"""
CashFlow REST API - FastAPI backend with complete feature set
JWT authentication, groups, expenses, balances, settlements
"""
import os
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from cashflow_api import CashFlowAPI, round_money
from auth_deps import hash_password, verify_password, create_access_token, get_current_user, User as AuthUser


# --- Pydantic Models ---

class UserCreate(BaseModel):
    name: str
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    username: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[int] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int
    is_archived: bool
    member_count: int
    created_at: str


class GroupDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int
    is_archived: bool
    created_at: str
    members: List[UserResponse]


class ExpenseSplitItem(BaseModel):
    user_id: int
    share: float


class ExpenseCreate(BaseModel):
    payer_id: int
    amount: float
    participant_ids: List[int] = []
    description: Optional[str] = None
    category: str = 'other'
    currency: str = 'RUB'
    split_type: str = 'equal'  # equal, percent, exact
    shares: Optional[dict] = None  # {user_id: percent or amount}
    group_id: Optional[int] = None
    expense_date: Optional[str] = None


class ExpenseEdit(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    split_type: Optional[str] = None
    participant_ids: Optional[List[int]] = None
    shares: Optional[dict] = None
    expense_date: Optional[str] = None


class ExpenseSplitResponse(BaseModel):
    user_id: int
    user_name: str
    share: float


class ExpenseResponse(BaseModel):
    id: int
    payer_id: int
    payer_name: str
    amount: float
    currency: str
    description: Optional[str]
    category: str
    split_type: str
    group_id: Optional[int]
    expense_date: str
    created_at: str
    splits: List[ExpenseSplitResponse] = []


class BalanceResponse(BaseModel):
    user_id: int
    user_name: str
    amount: float


class SettlementCreate(BaseModel):
    payer_id: int
    creditor_id: int
    amount: Optional[float] = None
    group_id: Optional[int] = None
    currency: str = 'RUB'


class SettlementResponse(BaseModel):
    success: bool
    message: str


class SettlementHistoryItem(BaseModel):
    id: int
    payer_id: int
    creditor_id: int
    amount: float
    currency: str
    created_at: str


class LinkCodeResponse(BaseModel):
    code: str
    expires_at: str


class LinkCodeConsume(BaseModel):
    code: str
    telegram_id: int
    first_name: str


class AddMemberRequest(BaseModel):
    user_id: int


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


# --- API Setup ---

db_path = os.getenv("CASHFLOW_DB", "cashflow.db")
cf = CashFlowAPI(db_path)

# Create demo data if empty
_users = cf.get_all_users()
if not _users:
    demo_pw = "$2b$12$LJ3m4ys3Lk0qJxqR5KGOuOZqKqR5KGOuOZqKqR5KGOuOZqKqR5KGOu"  # bcrypt placeholder
    alice = cf.register_user(telegram_id=1001, first_name="Alice", username="alice", email="alice@example.com", password_hash=demo_pw)
    bob = cf.register_user(telegram_id=1002, first_name="Bob", username="bob", email="bob@example.com", password_hash=demo_pw)
    charlie = cf.register_user(telegram_id=1003, first_name="Charlie", username="charlie", email="charlie@example.com", password_hash=demo_pw)

    # Create a demo group
    group = cf.create_group("Квартира", alice.id, "Расходы на квартиру")
    if group:
        cf.add_group_member(group.id, bob.id)
        cf.add_group_member(group.id, charlie.id)

        # Add some demo expenses
        from datetime import datetime
        cf.add_expense(
            payer_id=alice.id,
            amount=3000.0,
            description="Продукты",
            category="groceries",
            participant_ids=[bob.id, charlie.id],
            group_id=group.id,
            expense_date=datetime.utcnow(),
        )
        cf.add_expense(
            payer_id=bob.id,
            amount=1500.0,
            description="Коммунальные услуги",
            category="utilities",
            participant_ids=[alice.id, charlie.id],
            group_id=group.id,
            expense_date=datetime.utcnow(),
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="CashFlow API",
    description="REST API for shared expense tracking with groups, categories, and optimized debt settlement",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health ====================

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "CashFlow API", "version": "3.0.0"}


# ==================== Auth ====================

@app.post("/api/auth/register", response_model=TokenResponse)
def register(user: UserCreate):
    """Register a new user with email/password and get JWT token"""
    if not user.email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not user.password:
        raise HTTPException(status_code=400, detail="Password is required")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = cf.get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    pw_hash = hash_password(user.password)
    u = cf.register_user(
        first_name=user.name,
        username=user.username,
        email=user.email,
        password_hash=pw_hash,
    )
    cf.get_or_create_settings(u.id)

    token = create_access_token({"sub": u.id, "email": u.email})
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=u.id, name=u.first_name, username=u.username, email=u.email),
    )


@app.post("/api/auth/login", response_model=TokenResponse)
def login(creds: UserLogin):
    """Login with email/password and get JWT token"""
    user = cf.get_user_by_email(creds.email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        if not verify_password(creds.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception:
        # Hash format error (legacy data) — treat as invalid credentials
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, name=user.first_name, username=user.username, email=user.email),
    )


# ==================== Users ====================

@app.get("/api/users/me", response_model=UserResponse)
def get_current_user_info(current_user: AuthUser = Depends(get_current_user)):
    """Get current authenticated user"""
    return UserResponse(
        id=current_user.id, name=current_user.first_name,
        username=current_user.username, email=current_user.email,
        telegram_id=current_user.telegram_id,
    )


class UserSearchResult(BaseModel):
    id: int
    name: str
    email: Optional[str] = None


@app.get("/api/users", response_model=List[UserResponse])
def get_my_group_members(current_user: AuthUser = Depends(get_current_user)):
    """Get ONLY users who share a group with the current user (not all users)"""
    session = cf.db.get_session()
    try:
        from sqlalchemy import text
        # Find all user IDs who share any group with current_user
        rows = session.execute(text("""
            SELECT DISTINCT u.id, u.first_name, u.username, u.email, u.telegram_id
            FROM users u
            JOIN group_members gm1 ON gm1.user_id = u.id
            JOIN group_members gm2 ON gm2.group_id = gm1.group_id
            WHERE gm2.user_id = :uid AND u.id != :uid
        """), {"uid": current_user.id}).fetchall()
    finally:
        session.close()

    return [
        UserResponse(id=r[0], name=r[1], username=r[2], email=r[3], telegram_id=r[4])
        for r in rows
    ]


@app.get("/api/users/search")
def search_users(query: str, current_user: AuthUser = Depends(get_current_user)):
    """Search users by email or name (for inviting to groups)"""
    if not query or len(query) < 2:
        return []
    session = cf.db.get_session()
    try:
        from sqlalchemy import text
        rows = session.execute(text("""
            SELECT id, first_name, email FROM users
            WHERE email LIKE :q OR first_name LIKE :q
            LIMIT 10
        """), {"q": f"%{query}%"}).fetchall()
    finally:
        session.close()

    return [UserSearchResult(id=r[0], name=r[1], email=r[2]) for r in rows]


@app.post("/api/users", response_model=UserResponse)
def create_user(user: UserCreate, current_user: AuthUser = Depends(get_current_user)):
    """Register a new user (auth required, uses creator's context)"""
    u = cf.register_user(
        first_name=user.name,
        username=user.username,
        email=user.email,
    )
    cf.get_or_create_settings(u.id)
    return UserResponse(id=u.id, name=u.first_name, username=u.username, email=u.email)


@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: AuthUser = Depends(get_current_user)):
    """Get user by internal ID (auth required)"""
    u = cf.get_user_by_internal_id(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(id=u.id, name=u.first_name, username=u.username, email=u.email, telegram_id=u.telegram_id)


# ==================== Telegram Linking ====================

@app.post("/api/telegram/generate-code/{user_id}", response_model=LinkCodeResponse)
def generate_telegram_link_code(user_id: int):
    """Generate a code to link Telegram account"""
    code = cf.generate_link_code(user_id)
    if not code:
        raise HTTPException(status_code=404, detail="User not found")
    user = cf.get_user_by_internal_id(user_id)
    return LinkCodeResponse(
        code=code,
        expires_at=str(datetime.utcnow() + timedelta(hours=24)),
    )


@app.post("/api/telegram/link", response_model=UserResponse)
def link_telegram_account(data: LinkCodeConsume):
    """Link Telegram account using a code"""
    user = cf.consume_link_code(data.code, data.telegram_id, data.first_name)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    return UserResponse(id=user.id, name=user.first_name, username=user.username, email=user.email, telegram_id=user.telegram_id)


# ==================== Groups ====================

@app.post("/api/groups", response_model=GroupResponse)
def create_group(group: GroupCreate, current_user: AuthUser = Depends(get_current_user)):
    """Create a new group (auth required, user becomes creator)"""
    if not group.name.strip():
        raise HTTPException(status_code=400, detail="Group name is required")

    g = cf.create_group(group.name, current_user.id, group.description)
    if not g:
        raise HTTPException(status_code=500, detail="Failed to create group")

    return GroupResponse(
        id=g.id, name=g.name, description=g.description,
        created_by=g.created_by, is_archived=g.is_archived,
        member_count=1, created_at=str(g.created_at),
    )


@app.get("/api/groups", response_model=List[GroupResponse])
def get_user_groups(current_user: AuthUser = Depends(get_current_user)):
    """Get all groups for the current user"""
    groups = cf.get_user_groups(current_user.id)
    result = []
    for g in groups:
        members = cf.get_group_members(g.id)
        result.append(GroupResponse(
            id=g.id, name=g.name, description=g.description,
            created_by=g.created_by, is_archived=g.is_archived,
            member_count=len(members), created_at=str(g.created_at),
        ))
    return result


@app.get("/api/groups/{group_id}", response_model=GroupDetailResponse)
def get_group(group_id: int, current_user: AuthUser = Depends(get_current_user)):
    """Get group details with members (auth required)"""
    g = cf.get_group(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")

    members = cf.get_group_members(group_id)
    return GroupDetailResponse(
        id=g.id, name=g.name, description=g.description,
        created_by=g.created_by, is_archived=g.is_archived,
        created_at=str(g.created_at),
        members=[UserResponse(id=m.id, name=m.first_name, username=m.username) for m in members],
    )


@app.post("/api/groups/{group_id}/members")
def add_group_member(group_id: int, req: AddMemberRequest, current_user: AuthUser = Depends(get_current_user)):
    """Add a member to a group by user ID (auth required)"""
    success, message = cf.add_group_member(group_id, req.user_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


class AddMemberByEmail(BaseModel):
    email: str
    name: Optional[str] = None


@app.post("/api/groups/{group_id}/members-by-email")
def add_member_by_email(group_id: int, req: AddMemberByEmail, current_user: AuthUser = Depends(get_current_user)):
    """Add a member to a group by email. Creates user if not found."""
    if not req.email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Find existing user by email
    user = cf.get_user_by_email(req.email)

    if not user:
        # Create new user
        pw_hash = "$2b$12$placeholder"  # Set password later
        user = cf.register_user(
            first_name=req.name or req.email.split('@')[0],
            email=req.email,
            password_hash=pw_hash,
        )
        cf.get_or_create_settings(user.id)

    # Add to group
    success, message = cf.add_group_member(group_id, user.id)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message, "user_id": user.id, "user_name": user.first_name}


@app.delete("/api/groups/{group_id}/members/{user_id}")
def remove_group_member(group_id: int, user_id: int, current_user: AuthUser = Depends(get_current_user)):
    """Remove a member from a group (auth required)"""
    success, message = cf.remove_group_member(group_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@app.post("/api/groups/{group_id}/archive")
def archive_group(group_id: int, current_user: AuthUser = Depends(get_current_user)):
    """Archive a group (auth required, creator only)"""
    success, message = cf.archive_group(group_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


# ==================== Expenses ====================

@app.get("/api/expenses", response_model=List[ExpenseResponse])
def get_expenses(
    limit: int = 50, group_id: int = None,
    category: str = None, date_from: str = None, date_to: str = None,
    current_user: AuthUser = Depends(get_current_user),
):
    """Get expenses for current user with optional filters"""
    date_from_dt = datetime.fromisoformat(date_from) if date_from else None
    date_to_dt = datetime.fromisoformat(date_to) if date_to else None

    if group_id:
        expenses = cf.get_group_expenses(
            group_id, limit=limit, category=category,
            date_from=date_from_dt, date_to=date_to_dt
        )
    else:
        expenses = cf.get_user_expenses(
            current_user.id, limit=limit, group_id=group_id,
            category=category, date_from=date_from_dt, date_to=date_to_dt
        )

    result = []
    for e in expenses:
        splits = []
        if hasattr(e, 'splits') and e.splits:
            for s in e.splits:
                splits.append(ExpenseSplitResponse(
                    user_id=s.user_id,
                    user_name=s.user.first_name if s.user else 'Unknown',
                    share=s.share,
                ))

        payer_name = 'Unknown'
        if hasattr(e, 'payer') and e.payer:
            payer_name = e.payer.first_name
        else:
            p = cf.get_user_by_internal_id(e.payer_id)
            if p:
                payer_name = p.first_name

        result.append(ExpenseResponse(
            id=e.id,
            payer_id=e.payer_id,
            payer_name=payer_name,
            amount=e.amount,
            currency=e.currency,
            description=e.description,
            category=e.category,
            split_type=e.split_type,
            group_id=e.group_id,
            expense_date=str(e.expense_date),
            created_at=str(e.created_at),
            splits=splits,
        ))
    return result


@app.post("/api/expenses", response_model=dict)
def add_expense(expense: ExpenseCreate, current_user: AuthUser = Depends(get_current_user)):
    """Add a shared expense (auth required)"""
    expense_date = None
    if expense.expense_date:
        try:
            expense_date = datetime.fromisoformat(expense.expense_date)
        except ValueError:
            pass

    result, error = cf.add_expense(
        payer_id=expense.payer_id,
        amount=expense.amount,
        split_type=expense.split_type,
        participant_ids=expense.participant_ids,
        shares=expense.shares,
        description=expense.description,
        category=expense.category,
        currency=expense.currency,
        group_id=expense.group_id,
        expense_date=expense_date,
    )

    if not result:
        raise HTTPException(status_code=400, detail=error)

    payer = cf.get_user_by_internal_id(result.payer_id)
    splits_data = []
    if hasattr(result, 'splits') and result.splits:
        for s in result.splits:
            splits_data.append({
                'user_id': s.user_id,
                'user_name': s.user.first_name if s.user else 'Unknown',
                'share': s.share,
            })

    return {
        "id": result.id,
        "payer_id": result.payer_id,
        "payer_name": payer.first_name if payer else "Unknown",
        "amount": result.amount,
        "currency": result.currency,
        "description": result.description,
        "category": result.category,
        "split_type": result.split_type,
        "group_id": result.group_id,
        "expense_date": str(result.expense_date),
        "splits": splits_data,
    }


@app.put("/api/expenses/{expense_id}")
def edit_expense(expense_id: int, data: ExpenseEdit, current_user: AuthUser = Depends(get_current_user)):
    """Edit an expense (auth required)"""
    expense_date = None
    if data.expense_date:
        try:
            expense_date = datetime.fromisoformat(data.expense_date)
        except ValueError:
            pass

    success, message = cf.edit_expense(
        expense_id=expense_id,
        amount=data.amount,
        description=data.description,
        category=data.category,
        split_type=data.split_type,
        participant_ids=data.participant_ids,
        shares=data.shares,
        expense_date=expense_date,
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int, current_user: AuthUser = Depends(get_current_user)):
    """Delete an expense (auth required)"""
    success, message = cf.delete_expense(expense_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


# ==================== Balances ====================

@app.get("/api/balances/{user_id}", response_model=List[BalanceResponse])
def get_balances(user_id: int, group_id: int = None, current_user: AuthUser = Depends(get_current_user)):
    """Get balance overview for a user (auth required)"""
    user = cf.get_user_by_internal_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    balances = cf.get_user_balances(user_id, group_id=group_id)
    return [
        BalanceResponse(user_id=b["user_id"], user_name=b["user"], amount=b["amount"])
        for b in balances
    ]


@app.get("/api/balances/all")
def get_all_balances():
    """Get complete balance overview"""
    users = cf.get_all_users()
    all_balances = []
    for user in users:
        balances = cf.get_user_balances(user.id)
        for b in balances:
            if b['amount'] < 0:  # user.id owes money
                all_balances.append({
                    "debtor_id": user.id,
                    "debtor_name": user.first_name,
                    "creditor_id": b["user_id"],
                    "creditor_name": b["user"],
                    "amount": abs(b["amount"]),
                })
    return all_balances


@app.get("/api/balances/group/{group_id}")
def get_group_balances(group_id: int):
    """Get all balances within a group"""
    group = cf.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    balances = cf.get_group_balances(group_id)
    return balances


@app.get("/api/balances/total/{user_id}")
def get_user_total_balance(user_id: int, current_user: AuthUser = Depends(get_current_user)):
    """Get user's total balance across all groups"""
    return cf.get_user_total_balance(user_id)


# ==================== Optimized Settlements ====================

@app.get("/api/optimize-settlements")
def get_optimized_settlements(group_id: int = None, current_user: AuthUser = Depends(get_current_user)):
    """Get optimized settlement plan for current user (minimum transactions)"""
    return cf.get_optimized_settlements(user_id=current_user.id, group_id=group_id)


# ==================== Settlements ====================

@app.post("/api/settle", response_model=SettlementResponse)
def settle_balance(settlement: SettlementCreate, current_user: AuthUser = Depends(get_current_user)):
    """Record a settlement payment (auth required)"""
    success, message = cf.settle_balance(
        user1_id=settlement.payer_id,
        user2_id=settlement.creditor_id,
        amount=settlement.amount,
        group_id=settlement.group_id,
        currency=settlement.currency,
    )
    return SettlementResponse(success=success, message=message)


@app.get("/api/settlements", response_model=List[SettlementHistoryItem])
def get_settlement_history(group_id: int = None, limit: int = 50, current_user: AuthUser = Depends(get_current_user)):
    """Get settlement history for current user"""
    settlements = cf.get_settlement_history(user_id=current_user.id, group_id=group_id, limit=limit)
    return [
        SettlementHistoryItem(
            id=s.id,
            payer_id=s.payer_id,
            creditor_id=s.creditor_id,
            amount=s.amount,
            currency=s.currency,
            created_at=str(s.created_at),
        )
        for s in settlements
    ]


# ==================== Categories & Currencies ====================

@app.get("/api/categories")
def get_categories():
    """Get available expense categories"""
    return cf.get_categories()


@app.get("/api/currencies")
def get_currencies():
    """Get available currencies"""
    return cf.get_currencies()


# ==================== Digest & Notifications ====================

@app.get("/api/digest/{user_id}")
def get_weekly_digest(user_id: int):
    """Get weekly digest for a user"""
    user = cf.get_user_by_internal_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return cf.get_weekly_digest(user_id)


@app.get("/api/overdue-debts")
def get_overdue_debts(days: int = 7):
    """Get users with overdue debts"""
    return cf.get_users_with_overdue_debts(days)


# ==================== Statistics ====================

@app.get("/api/stats")
def get_stats(current_user: AuthUser = Depends(get_current_user)):
    """Get statistics for the CURRENT USER only (not global)"""
    session = cf.db.get_session()
    try:
        from sqlalchemy import text

        # Count groups user is a member of
        group_count = session.execute(
            text("SELECT COUNT(*) FROM group_members WHERE user_id = :uid"),
            {"uid": current_user.id}
        ).scalar()

        # Count expenses where user is payer OR participant
        expense_count = session.execute(
            text("""
                SELECT COUNT(*) FROM expenses e
                WHERE e.payer_id = :uid
                OR e.id IN (SELECT es.expense_id FROM expense_splits es WHERE es.user_id = :uid)
            """),
            {"uid": current_user.id}
        ).scalar()

        # Total expenses involving this user
        total_expenses = session.execute(
            text("""
                SELECT COALESCE(SUM(e.amount), 0) FROM expenses e
                WHERE e.payer_id = :uid
                OR e.id IN (SELECT es.expense_id FROM expense_splits es WHERE es.user_id = :uid)
            """),
            {"uid": current_user.id}
        ).scalar()

        # Settlements where user is payer OR creditor
        settlement_count = session.execute(
            text("SELECT COUNT(*) FROM settlements WHERE payer_id = :uid OR creditor_id = :uid"),
            {"uid": current_user.id}
        ).scalar()

        total_settled = session.execute(
            text("SELECT COALESCE(SUM(amount), 0) FROM settlements WHERE payer_id = :uid OR creditor_id = :uid"),
            {"uid": current_user.id}
        ).scalar()
    finally:
        session.close()

    return {
        "users": group_count,  # Show group count instead of user count
        "groups": group_count,
        "expenses": expense_count,
        "total_expenses": round(float(total_expenses), 2),
        "settlements": settlement_count,
        "total_settled": round(float(total_settled), 2),
    }


# ==================== Serve Frontend ====================

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{full_path:path}")
    def serve_static(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
