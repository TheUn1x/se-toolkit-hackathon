/* CashFlow — Web App Logic (Complete, Logical) */

const API = window.location.origin;

// ===== STATE =====
let users = [];
let groups = [];
let currentUser = null;
let authToken = localStorage.getItem('cf_token') || null;
let currentGroupId = null;

// ===== API =====
async function apiGet(url) {
    const headers = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(API + url, { headers });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        if (res.status === 401) { doLogout(); throw new Error('Сессия истекла'); }
        throw new Error(err.detail || `Ошибка (${res.status})`);
    }
    return res.json();
}

async function apiPost(url, data) {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(API + url, { method: 'POST', headers, body: JSON.stringify(data) });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        if (res.status === 401) { doLogout(); throw new Error('Сессия истекла'); }
        throw new Error(err.detail || `Ошибка (${res.status})`);
    }
    return res.json();
}

function doLogout() {
    authToken = null; currentUser = null;
    localStorage.removeItem('cf_token');
    showAuth();
}

// ===== HELPERS =====
function el(id) { return document.getElementById(id); }
function val(id) { const e = el(id); return e ? e.value.trim() : ''; }
function setTxt(id, txt) { const e = el(id); if (e) e.textContent = txt; }
function setHtml(id, html) { const e = el(id); if (e) e.innerHTML = html; }
function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function fmtDate(s) { if (!s) return ''; try { const d = new Date(s); return d.toLocaleDateString('ru-RU') + ' ' + d.toLocaleTimeString('ru-RU', { hour:'2-digit', minute:'2-digit' }); } catch { return s; } }
function pluralRu(n) { n = Math.abs(n) % 100; const r = n % 10; if (n > 10 && n < 20) return 'ов'; if (r === 1) return ''; if (r >= 2 && r <= 4) return 'а'; return 'ов'; }
function toast(msg, type = 'success') { const t = el('toast'); if (!t) return; t.textContent = msg; t.className = `toast show ${type}`; setTimeout(() => { t.className = 'toast hidden'; }, 3000); }

// ===== INIT =====
document.addEventListener('DOMContentLoaded', async () => {
    setupAuthForms(); // Always first
    if (authToken) {
        try { currentUser = await apiGet('/api/users/me'); showApp(); }
        catch { showAuth(); }
    } else { showAuth(); }
});

function showAuth() { el('auth-screen').classList.remove('hidden'); el('app-screen').classList.add('hidden'); }
function showApp() {
    el('auth-screen').classList.add('hidden'); el('app-screen').classList.remove('hidden');
    setTxt('current-user-name', currentUser.name);
    initApp();
}

async function initApp() {
    await Promise.allSettled([loadUsers(), loadGroups(), loadStats(), loadDashboard()]);
    setupTabs();
    setupExpenseForm();
    setupSettleForm();
    setupGroupForm();
    setupAddMemberForm();
    setupOptimizeBtn();
    setupFilters();
    setupGroupActions();
}

// ===== AUTH =====
let authFormsSetup = false;
function setupAuthForms() {
    if (authFormsSetup) return; authFormsSetup = true;
    el('show-register')?.addEventListener('click', e => { e.preventDefault(); el('login-form').classList.add('hidden'); el('register-form').classList.remove('hidden'); });
    el('show-login')?.addEventListener('click', e => { e.preventDefault(); el('register-form').classList.add('hidden'); el('login-form').classList.remove('hidden'); });
    el('signin-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        try {
            const r = await apiPost('/api/auth/login', { email: val('login-email'), password: val('login-password') });
            authToken = r.access_token; currentUser = r.user;
            localStorage.setItem('cf_token', authToken); showApp(); toast('Добро пожаловать!', 'success');
        } catch (err) { toast(err.message, 'error'); }
    });
    el('signup-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        try {
            const r = await apiPost('/api/auth/register', { name: val('reg-name'), email: val('reg-email'), password: val('reg-password') });
            authToken = r.access_token; currentUser = r.user;
            localStorage.setItem('cf_token', authToken); showApp(); toast('Аккаунт создан!', 'success');
        } catch (err) { toast(err.message, 'error'); }
    });
    el('logout-btn')?.addEventListener('click', doLogout);
}

// ===== TABS =====
function setupTabs() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            const tab = el('tab-' + btn.dataset.tab); if (tab) tab.classList.add('active');
            if (btn.dataset.tab === 'groups') { loadGroups(); el('groups-list-view').classList.remove('hidden'); el('group-detail').classList.add('hidden'); }
            if (btn.dataset.tab === 'expenses') loadExpenses();
            if (btn.dataset.tab === 'balances') loadBalancesTab();
            if (btn.dataset.tab === 'settle') loadSettleTab();
        };
    });
}

// ===== USERS =====
async function loadUsers() {
    try { users = await apiGet('/api/users'); } catch { users = []; }
    populateUserSelects();
}

function populateUserSelects() {
    ['qe-payer','settle-payer','settle-creditor'].forEach(id => {
        const sel = el(id); if (!sel) return;
        const ph = { 'qe-payer':'Кто заплатил?', 'settle-payer':'Кто платит?', 'settle-creditor':'Кому?' };
        sel.innerHTML = `<option value="">${ph[id] || ''}</option>`;
        users.forEach(u => { sel.innerHTML += `<option value="${u.id}">${esc(u.name)}</option>`; });
    });
}

// ===== GROUPS =====
async function loadGroups() {
    try {
        groups = await apiGet('/api/groups');
        populateGroupSelects();
        renderGroupsList();
        renderDashGroups();
    } catch (e) { console.error('Groups:', e); }
}

function populateGroupSelects() {
    ['qe-group','exp-group-filter','balance-group-filter','optimize-group'].forEach(id => {
        const sel = el(id); if (!sel) return;
        const first = sel.querySelector('option'); sel.innerHTML = '';
        if (first) sel.appendChild(first.cloneNode(true));
        (groups || []).filter(g => !g.is_archived).forEach(g => {
            sel.innerHTML += `<option value="${g.id}">${esc(g.name)}</option>`;
        });
    });
}

function renderGroupsList() {
    const c = el('groups-list'); if (!c) return;
    if (!groups || !groups.length) { c.innerHTML = '<p class="empty-state">Нет групп. Создайте первую!</p>'; return; }
    c.innerHTML = groups.map(g => `
        <div class="group-item" onclick="openGroupDetail(${g.id})">
            <div class="group-info">
                <div class="group-name">${esc(g.name)}</div>
                <div class="group-desc-text">${esc(g.description || '')}</div>
                <div class="group-meta">${g.member_count} участник${pluralRu(g.member_count)}</div>
            </div>
            ${g.is_archived ? '<span class="badge badge-archived">Архив</span>' : ''}
        </div>`).join('');
}

function renderDashGroups() {
    const c = el('dash-groups-list'); if (!c) return;
    const active = (groups || []).filter(g => !g.is_archived);
    if (!active.length) { c.innerHTML = '<p class="empty-state">Создайте группу на вкладке «Группы»</p>'; return; }
    c.innerHTML = active.map(g => `
        <div class="group-item" onclick="openGroupDetail(${g.id})">
            <div class="group-info">
                <div class="group-name">${esc(g.name)}</div>
                <div class="group-meta">${g.member_count} участник${pluralRu(g.member_count)}</div>
            </div>
        </div>`).join('');
}

// ===== GROUP DETAIL =====
async function openGroupDetail(groupId) {
    currentGroupId = groupId;
    try {
        const group = await apiGet(`/api/groups/${groupId}`);
        el('groups-list-view').classList.add('hidden');
        el('group-detail').classList.remove('hidden');
        setTxt('gd-name', group.name);
        setTxt('gd-desc', group.description || 'Без описания');
        setTxt('gd-members-count', `${group.members.length} участник${pluralRu(group.members.length)}`);
        el('gd-archived').classList.toggle('hidden', !group.is_archived);

        // Members
        const ml = el('gd-members-list');
        if (ml) {
            ml.innerHTML = (group.members || []).map(m => `
                <div class="member-item">
                    <span>${esc(m.name)} ${esc(m.email ? '(' + m.email + ')' : '')}</span>
                    <span class="badge ${m.id === group.created_by ? 'badge-creator' : 'badge-member'}">
                        ${m.id === group.created_by ? 'Создатель' : 'Участник'}
                    </span>
                </div>`).join('');
        }

        // Clear add member form
        el('gd-add-email').value = '';
        el('gd-add-name').value = '';

        // Balances
        try {
            const balances = await apiGet(`/api/balances/group/${groupId}`);
            setHtml('gd-balances', !balances.length
                ? '<p class="empty-state">✅ Все долги погашены</p>'
                : balances.map(b => `<div class="balance-item">
                    <span class="balance-name">${esc(b.debtor_name)} должен ${esc(b.creditor_name)}</span>
                    <span class="balance-amount owes">${b.amount.toFixed(2)} ₽</span>
                </div>`).join(''));
        } catch { setHtml('gd-balances', '<p class="empty-state">Ошибка</p>'); }

        // Expenses
        try {
            const expenses = await apiGet(`/api/expenses?group_id=${groupId}&limit=50`);
            renderExpensesIn(expenses, 'gd-expenses');
        } catch { setHtml('gd-expenses', '<p class="empty-state">Ошибка</p>'); }

        // Show/hide leave & archive buttons
        const isCreator = group.created_by === currentUser.id;
        const leaveBtn = el('gd-leave-btn');
        const archiveBtn = el('gd-archive-btn');
        if (leaveBtn) leaveBtn.style.display = 'inline-block';
        if (archiveBtn) archiveBtn.style.display = isCreator ? 'inline-block' : 'none';

    } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

el('group-back-btn')?.addEventListener('click', () => {
    el('group-detail').classList.add('hidden');
    el('groups-list-view').classList.remove('hidden');
    currentGroupId = null;
});

// ===== ADD MEMBER BY EMAIL =====
function setupAddMemberForm() {
    el('gd-add-member-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        const email = val('gd-add-email');
        if (!email) { toast('Введите email', 'error'); return; }
        try {
            const name = val('gd-add-name') || null;
            const r = await apiPost(`/api/groups/${currentGroupId}/members-by-email`, { email, name });
            toast(r.message, 'success');
            openGroupDetail(currentGroupId); // refresh
            loadUsers(); // refresh user list
        } catch (err) { toast(err.message, 'error'); }
    });
}

// ===== GROUP ACTIONS (leave, archive) =====
function setupGroupActions() {
    el('gd-leave-btn')?.addEventListener('click', async () => {
        if (!currentUser || !currentGroupId) return;
        if (!confirm('Вы уверены что хотите покинуть эту группу?')) return;
        try {
            await apiDelete(`/api/groups/${currentGroupId}/members/${currentUser.id}`);
            toast('Вы покинули группу', 'success');
            el('group-detail').classList.add('hidden');
            el('groups-list-view').classList.remove('hidden');
            loadGroups();
        } catch (err) { toast(err.message, 'error'); }
    });

    el('gd-archive-btn')?.addEventListener('click', async () => {
        if (!currentGroupId) return;
        if (!confirm('Архивировать группу?')) return;
        try {
            await apiPost(`/api/groups/${currentGroupId}/archive?user_id=${currentUser.id}`, {});
            toast('Группа архивирована', 'success');
            loadGroups();
            openGroupDetail(currentGroupId);
        } catch (err) { toast(err.message, 'error'); }
    });
}

// ===== CREATE GROUP =====
function setupGroupForm() {
    el('create-group-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        const name = val('cg-name');
        if (!name) { toast('Введите название', 'error'); return; }
        try {
            await apiPost('/api/groups', { name, description: val('cg-desc') || null });
            el('cg-name').value = ''; el('cg-desc').value = '';
            await loadGroups(); await loadStats();
            toast('Группа создана! Вы автоматически добавлены.', 'success');
        } catch (err) { toast(err.message, 'error'); }
    });
}

// ===== DASHBOARD =====
async function loadDashboard() {
    if (!currentUser) return;
    try {
        const total = await apiGet(`/api/balances/total/${currentUser.id}`);
        setHtml('my-balance', `
            <div class="bal-row"><span class="bal-label">Мне должны:</span><span class="bal-val green">${total.total_owed.toFixed(2)} ₽</span></div>
            <div class="bal-row"><span class="bal-label">Я должен:</span><span class="bal-val red">${total.total_owes.toFixed(2)} ₽</span></div>
            <div class="bal-row"><span class="bal-label">Нетто:</span><span class="bal-val ${total.net >= 0 ? 'green' : 'red'}">${total.net.toFixed(2)} ₽</span></div>`);
    } catch { setHtml('my-balance', '<p class="empty-state">Ошибка загрузки</p>'); }
    try {
        const s = await apiGet('/api/stats');
        setTxt('stat-groups', s.groups); setTxt('stat-expenses', s.expenses);
        setTxt('stat-total', s.total_expenses.toFixed(2) + ' ₽');
        setTxt('stat-settled', s.total_settled.toFixed(2) + ' ₽');
    } catch {}
}

// ===== EXPENSE FORM =====
function setupExpenseForm() {
    el('qe-group')?.addEventListener('change', updateParticipants);
    el('qe-payer')?.addEventListener('change', updateParticipants);
    if (currentUser) setTimeout(() => { el('qe-payer').value = currentUser.id; updateParticipants(); }, 200);

    el('quick-expense-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        const resultDiv = el('qe-result'); if (resultDiv) resultDiv.classList.add('hidden');
        const payerId = parseInt(val('qe-payer'));
        const amount = parseFloat(val('qe-amount'));
        if (!payerId) { toast('Выберите кто заплатил', 'error'); return; }
        if (!amount || amount <= 0) { toast('Введите сумму', 'error'); return; }

        const participantIds = [];
        document.querySelectorAll('#qe-participants input:checked').forEach(cb => participantIds.push(parseInt(cb.value)));
        if (!participantIds.length) { toast('Выберите хотя бы одного участника', 'error'); return; }

        const data = {
            payer_id: payerId, amount, participant_ids: participantIds,
            description: val('qe-desc') || null, category: val('qe-category') || 'other',
            currency: val('qe-currency') || 'RUB', split_type: val('qe-split-type') || 'equal',
        };
        const gId = val('qe-group');
        if (gId) data.group_id = parseInt(gId);

        try {
            const r = await apiPost('/api/expenses', data);
            if (resultDiv) {
                resultDiv.textContent = `✅ ${r.payer_name} заплатил ${r.amount.toFixed(2)} ${r.currency} — разделено на ${r.splits.length} чел.`;
                resultDiv.className = 'result success'; resultDiv.classList.remove('hidden');
            }
            el('qe-amount').value = ''; el('qe-desc').value = '';
            await Promise.allSettled([loadStats(), loadDashboard()]);
            toast('Трата добавлена!', 'success');
        } catch (err) {
            if (resultDiv) { resultDiv.textContent = '❌ ' + err.message; resultDiv.className = 'result error'; resultDiv.classList.remove('hidden'); }
            toast(err.message, 'error');
        }
    });
}

function updateParticipants() {
    const groupId = val('qe-group') ? parseInt(val('qe-group')) : null;
    const payerId = parseInt(val('qe-payer') || 0);
    const container = el('qe-participants'); if (!container) return;

    let list;
    if (groupId) {
        const group = groups.find(g => g.id === groupId);
        // If group selected: use group members, auto-add payer if not in group
        if (group && group.members && group.members.length > 0) {
            // Check if payer is in group; if not, show a note
            const payerInGroup = group.members.some(m => m.id === payerId);
            if (!payerInGroup) {
                container.innerHTML = `<p class="hint" style="color:#fc8181;">⚠️ Плательщик не в этой группе. Участники:</p>`
                    + group.members.filter(m => m.id !== payerId).map(u =>
                        `<label class="participant-checkbox"><input type="checkbox" value="${u.id}" checked> ${esc(u.name)}</label>`
                    ).join('');
                return;
            }
            list = group.members.filter(m => m.id !== payerId);
        } else {
            // Group has no members yet — show all users except payer
            list = users.filter(u => u.id !== payerId);
        }
    } else {
        // No group — all users except payer
        list = users.filter(u => u.id !== payerId);
    }

    container.innerHTML = '<p class="hint">Разделить с:</p>'
        + list.map(u => `<label class="participant-checkbox"><input type="checkbox" value="${u.id}" checked> ${esc(u.name)}</label>`).join('');
}

// ===== EXPENSES =====
async function loadExpenses(filters = {}) {
    try {
        const params = new URLSearchParams({ limit: 200 });
        if (filters.group_id) params.set('group_id', filters.group_id);
        if (filters.category) params.set('category', filters.category);
        if (filters.date_from) params.set('date_from', filters.date_from);
        if (filters.date_to) params.set('date_to', filters.date_to);
        const expenses = await apiGet('/api/expenses?' + params);
        renderExpensesIn(expenses, 'expenses-list');
    } catch (e) { setHtml('expenses-list', `<p class="empty-state">Ошибка: ${esc(e.message)}</p>`); }
}

function renderExpensesIn(expenses, containerId) {
    const c = el(containerId); if (!c) return;
    if (!expenses || !expenses.length) { c.innerHTML = '<p class="empty-state">Трат нет</p>'; return; }
    const emoji = { food:'🍔', transport:'🚗', housing:'🏠', entertainment:'🎬', utilities:'💡', groceries:'🛒', other:'📦' };
    c.innerHTML = expenses.map(e => `
        <div class="expense-item">
            <div class="expense-info">
                <div class="expense-desc">${esc(e.description || 'Без описания')}</div>
                <div class="expense-meta">
                    Заплатил(а) <strong>${esc(e.payer_name)}</strong>
                    · ${fmtDate(e.expense_date || e.created_at)}
                    · ${e.splits?.length || 0} чел.
                    <span class="expense-category">${emoji[e.category] || '📦'} ${e.category}</span>
                </div>
            </div>
            <div class="expense-amount">${e.amount.toFixed(2)} ${e.currency || '₽'}</div>
        </div>`).join('');
}

function setupFilters() {
    el('exp-apply-filters')?.addEventListener('click', () => loadExpenses({
        group_id: val('exp-group-filter') || null, category: val('exp-category-filter') || null,
        date_from: val('exp-date-from') || null, date_to: val('exp-date-to') || null,
    }));
    el('exp-clear-filters')?.addEventListener('click', () => {
        el('exp-group-filter').value = ''; el('exp-category-filter').value = '';
        el('exp-date-from').value = ''; el('exp-date-to').value = ''; loadExpenses();
    });
}

// ===== BALANCES =====
async function loadBalancesTab() { if (currentUser) loadMyBalances(); }

async function loadMyBalances() {
    if (!currentUser) return;
    setHtml('my-balances-list', '<p class="empty-state">Загрузка...</p>');
    try {
        const gId = val('balance-group-filter') || null;
        const url = gId ? `/api/balances/${currentUser.id}?group_id=${gId}` : `/api/balances/${currentUser.id}`;
        const balances = await apiGet(url);
        setHtml('my-balances-list', !balances.length ? '<p class="empty-state">✅ Нет долгов</p>' : balances.map(b => {
            const owed = b.amount > 0;
            return `<div class="balance-item"><span class="balance-name">${esc(b.user_name)} <span class="balance-label">${owed ? 'должен(а) вам' : 'вы должны'}</span></span><span class="balance-amount ${owed ? 'owed' : 'owes'}">${Math.abs(b.amount).toFixed(2)} ₽</span></div>`;
        }).join(''));
        const total = await apiGet(`/api/balances/total/${currentUser.id}`);
        setHtml('my-total-balance', `
            <div class="stat-row"><span>Вам должны:</span><span class="bal-val green">${total.total_owed.toFixed(2)} ₽</span></div>
            <div class="stat-row"><span>Вы должны:</span><span class="bal-val red">${total.total_owes.toFixed(2)} ₽</span></div>
            <div class="stat-row"><span>Нетто:</span><span class="bal-val ${total.net >= 0 ? 'green' : 'red'}">${total.net.toFixed(2)} ₽</span></div>`);
    } catch (e) { setHtml('my-balances-list', `<p class="empty-state">Ошибка: ${esc(e.message)}</p>`); }
}
el('balance-group-filter')?.addEventListener('change', loadMyBalances);

// ===== SETTLE =====
async function loadSettleTab() {
    if (!currentUser) return;
    await Promise.allSettled([loadIOwe(), loadOwesMe(), loadSettlementHistory()]);
}

async function loadIOwe() {
    try {
        const balances = await apiGet(`/api/balances/${currentUser.id}`);
        const iOwe = balances.filter(b => b.amount < 0);
        const c = el('i-owe-list'); if (!c) return;
        if (!iOwe.length) { c.innerHTML = '<p class="empty-state">✅ Вы никому не должны</p>'; return; }
        c.innerHTML = iOwe.map(b => `<div class="settle-quick-item">
            <div><div class="balance-name">${esc(b.user_name)}</div><div class="balance-label">Вы должны</div></div>
            <div style="display:flex;align-items:center;gap:12px;">
                <span class="settle-amount owes">${Math.abs(b.amount).toFixed(2)} ₽</span>
                <button class="btn btn-success" style="width:auto;padding:6px 12px;font-size:0.8rem;" onclick="quickSettle(${currentUser.id},${b.user_id})">Погасить</button>
            </div>
        </div>`).join('');
    } catch { setHtml('i-owe-list', '<p class="empty-state">Ошибка</p>'); }
}

async function loadOwesMe() {
    try {
        const balances = await apiGet(`/api/balances/${currentUser.id}`);
        const owesMe = balances.filter(b => b.amount > 0);
        const c = el('owe-me-list'); if (!c) return;
        if (!owesMe.length) { c.innerHTML = '<p class="empty-state">Вам никто не должен</p>'; return; }
        c.innerHTML = owesMe.map(b => `<div class="settle-quick-item">
            <div><div class="balance-name">${esc(b.user_name)}</div><div class="balance-label">Должен(а) вам</div></div>
            <span class="settle-amount owed">${b.amount.toFixed(2)} ₽</span>
        </div>`).join('');
    } catch { setHtml('owe-me-list', '<p class="empty-state">Ошибка</p>'); }
}

async function loadSettlementHistory() {
    try {
        const settlements = await apiGet('/api/settlements?limit=50');
        const c = el('settlements-list'); if (!c) return;
        if (!settlements.length) { c.innerHTML = '<p class="empty-state">Погашений нет</p>'; return; }
        c.innerHTML = settlements.map(s => {
            const payer = users.find(u => u.id === s.payer_id);
            const creditor = users.find(u => u.id === s.creditor_id);
            return `<div class="balance-item"><span class="balance-name">${esc(payer?.name || '?')} → ${esc(creditor?.name || '?')}</span><span class="balance-amount owed">${s.amount.toFixed(2)} ₽</span></div>`;
        }).join('');
    } catch { setHtml('settlements-list', '<p class="empty-state">Ошибка</p>'); }
}

async function quickSettle(payerId, creditorId) {
    try {
        const r = await apiPost('/api/settle', { payer_id: payerId, creditor_id: creditorId });
        toast(r.message, r.success ? 'success' : 'error');
        await loadSettleTab();
    } catch (err) { toast(err.message, 'error'); }
}
window.quickSettle = quickSettle;

function setupSettleForm() {
    el('settle-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        const resultDiv = el('settle-result'); if (resultDiv) resultDiv.classList.add('hidden');
        const payerId = parseInt(val('settle-payer'));
        const creditorId = parseInt(val('settle-creditor'));
        if (!payerId) { toast('Выберите кто платит', 'error'); return; }
        if (!creditorId) { toast('Выберите кому', 'error'); return; }
        if (payerId === creditorId) { toast('Нельзя платить самому себе', 'error'); return; }
        const amt = val('settle-amount');
        const data = { payer_id: payerId, creditor_id: creditorId, amount: amt ? parseFloat(amt) : null };
        try {
            const r = await apiPost('/api/settle', data);
            if (resultDiv) { resultDiv.textContent = r.success ? '✅ ' + r.message : '❌ ' + r.message; resultDiv.className = `result ${r.success ? 'success' : 'error'}`; resultDiv.classList.remove('hidden'); }
            if (r.success) { el('settle-amount').value = ''; await loadSettleTab(); toast('Погашено!', 'success'); }
        } catch (err) {
            if (resultDiv) { resultDiv.textContent = '❌ ' + err.message; resultDiv.className = 'result error'; resultDiv.classList.remove('hidden'); }
            toast(err.message, 'error');
        }
    });
}

// ===== OPTIMIZE =====
function setupOptimizeBtn() {
    el('optimize-btn')?.addEventListener('click', async () => {
        const c = el('optimize-result'); if (!c) return;
        c.innerHTML = '<p class="empty-state">Считаю...</p>';
        try {
            const gId = val('optimize-group');
            const url = gId ? `/api/optimize-settlements?group_id=${gId}` : '/api/optimize-settlements';
            const plan = await apiGet(url);
            if (!plan.length) { c.innerHTML = '<p class="empty-state">✅ Все долги погашены!</p>'; return; }
            c.innerHTML = plan.map((p, i) => `<div class="optimize-item">
                <span class="optimize-arrow">${i + 1}. ${esc(p.from_user_name)} → ${esc(p.to_user_name)}</span>
                <span class="expense-amount">${p.amount.toFixed(2)} ₽</span>
            </div>`).join('');
        } catch (err) { c.innerHTML = `<p class="empty-state">Ошибка: ${esc(err.message)}</p>`; }
    });
}

// ===== GLOBAL =====
window.openGroupDetail = openGroupDetail;
