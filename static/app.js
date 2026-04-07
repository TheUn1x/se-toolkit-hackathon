/* CashFlow — Web App JavaScript */

const API = window.location.origin;

// State
let users = [];
let groups = [];
let currentUser = null;
let authToken = localStorage.getItem('cashflow_token') || null;

// --- API Helpers with proper error handling ---
async function apiGet(url) {
    const headers = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    let res;
    try {
        res = await fetch(`${API}${url}`, { headers });
    } catch (e) {
        throw new Error('Network error — is the server running?');
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        if (res.status === 401) {
            logoutAndRedirect();
            throw new Error('Session expired. Please log in again.');
        }
        throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
}

async function apiPost(url, data) {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    let res;
    try {
        res = await fetch(`${API}${url}`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data),
        });
    } catch (e) {
        throw new Error('Network error — is the server running?');
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        if (res.status === 401) {
            logoutAndRedirect();
            throw new Error('Session expired. Please log in again.');
        }
        throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
}

async function apiPut(url, data) {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(`${API}${url}`, {
        method: 'PUT', headers, body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
}

async function apiDelete(url) {
    const headers = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(`${API}${url}`, { method: 'DELETE', headers });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
}

function logoutAndRedirect() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('cashflow_token');
    showAuth();
}

// --- Init ---
document.addEventListener('DOMContentLoaded', async () => {
    if (authToken) {
        try {
            currentUser = await apiGet('/api/users/me');
            showApp();
        } catch (e) {
            showAuth();
        }
    } else {
        showAuth();
    }
    setupAuthForms();
});

// --- Auth ---
function showAuth() {
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('app-screen').classList.add('hidden');
}

function showApp() {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('app-screen').classList.remove('hidden');
    if (currentUser) {
        document.getElementById('current-user-name').textContent = currentUser.name;
    }
    initApp();
}

async function initApp() {
    await Promise.allSettled([
        loadUsers(),
        loadGroups(),
        loadStats(),
        loadExpenses(),
        loadSettlements(),
    ]);
    setupForms();
    setupGroupForm();
    setupOptimizeButton();
    setupTabs();
}

function setupAuthForms() {
    document.getElementById('show-register')?.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-form').classList.remove('hidden');
    });
    document.getElementById('show-login')?.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('register-form').classList.add('hidden');
        document.getElementById('login-form').classList.remove('hidden');
    });
    document.getElementById('demo-link')?.addEventListener('click', (e) => {
        e.preventDefault();
        currentUser = { id: 0, name: 'Demo User' };
        showApp();
    });

    // Sign in
    document.getElementById('signin-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const result = await apiPost('/api/auth/login', {
                email: document.getElementById('login-email').value,
                password: document.getElementById('login-password').value,
            });
            authToken = result.access_token;
            currentUser = result.user;
            localStorage.setItem('cashflow_token', authToken);
            showApp();
            showToast('Signed in!', 'success');
        } catch (err) {
            showToast(err.message, 'error');
        }
    });

    // Sign up
    document.getElementById('signup-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const result = await apiPost('/api/auth/register', {
                name: document.getElementById('reg-name').value,
                username: document.getElementById('reg-username').value || null,
                email: document.getElementById('reg-email').value,
                password: document.getElementById('reg-password').value,
            });
            authToken = result.access_token;
            currentUser = result.user;
            localStorage.setItem('cashflow_token', authToken);
            showApp();
            showToast('Account created!', 'success');
        } catch (err) {
            showToast(err.message, 'error');
        }
    });

    // Logout
    document.getElementById('logout-btn')?.addEventListener('click', logoutAndRedirect);
}

// --- Tabs ---
function setupTabs() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            const tabId = `tab-${btn.dataset.tab}`;
            document.getElementById(tabId)?.classList.add('active');

            // Load data on tab switch
            if (btn.dataset.tab === 'groups') loadGroups();
            if (btn.dataset.tab === 'expenses') loadExpenses();
            if (btn.dataset.tab === 'balances') loadBalancesTab();
            if (btn.dataset.tab === 'settle') loadSettlements();
        });
    });
}

// --- Users ---
async function loadUsers() {
    try {
        users = await apiGet('/api/users');
        populateUserSelects();
    } catch (e) {
        console.error('Failed to load users:', e);
        users = [];
    }
}

function populateUserSelects() {
    const selects = ['qe-payer', 'balance-user', 'settle-payer', 'settle-creditor'];
    selects.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const firstOpt = el.querySelector('option');
        el.innerHTML = '';
        if (firstOpt) el.appendChild(firstOpt.cloneNode(true));
        users.forEach(u => {
            const opt = document.createElement('option');
            opt.value = u.id;
            opt.textContent = u.name;
            el.appendChild(opt);
        });
    });
    updateQuickExpenseParticipants();
}

// --- Groups ---
async function loadGroups() {
    try {
        groups = await apiGet('/api/groups');
        populateGroupSelects();
        renderGroups();
    } catch (e) {
        console.error('Failed to load groups:', e);
        const c = document.getElementById('groups-list');
        if (c) c.innerHTML = `<p class="empty-state">Error loading groups: ${esc(e.message)}</p>`;
    }
}

function populateGroupSelects() {
    const selects = ['qe-group', 'exp-group-filter', 'balance-group', 'settle-group', 'optimize-group'];
    selects.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const firstOpt = el.querySelector('option');
        el.innerHTML = '';
        if (firstOpt) el.appendChild(firstOpt.cloneNode(true));
        (groups || []).filter(g => !g.is_archived).forEach(g => {
            const opt = document.createElement('option');
            opt.value = g.id;
            opt.textContent = g.name;
            el.appendChild(opt);
        });
    });
}

function renderGroups() {
    const container = document.getElementById('groups-list');
    if (!container) return;
    if (!groups.length) {
        container.innerHTML = '<p class="empty-state">No groups yet. Create your first group!</p>';
        return;
    }
    container.innerHTML = groups.map(g => `
        <div class="group-item" data-group-id="${g.id}">
            <div class="group-info">
                <div class="group-name">${esc(g.name)}</div>
                <div class="group-desc-text">${esc(g.description || '')}</div>
                <div class="group-meta">${g.member_count} member${g.member_count !== 1 ? 's' : ''}</div>
            </div>
            ${g.is_archived ? '<span class="badge badge-archived">Archived</span>' : ''}
        </div>
    `).join('');

    container.querySelectorAll('.group-item').forEach(el => {
        el.addEventListener('click', () => openGroupDetail(parseInt(el.dataset.groupId)));
    });
}

async function openGroupDetail(groupId) {
    try {
        const group = await apiGet(`/api/groups/${groupId}`);
        document.getElementById('groups-list').classList.add('hidden');
        const h2 = document.getElementById('create-group-form')?.parentElement?.querySelector('h2');
        if (h2) h2.classList.add('hidden');
        document.getElementById('create-group-form')?.classList.add('hidden');

        document.getElementById('group-detail').classList.remove('hidden');
        document.getElementById('gd-name').textContent = group.name;
        document.getElementById('gd-desc').textContent = group.description || 'No description';
        document.getElementById('gd-members').textContent = `${group.members.length} members`;

        const badge = document.getElementById('gd-archived');
        badge?.classList.toggle('hidden', !group.is_archived);

        // Members
        const membersList = document.getElementById('gd-members-list');
        if (membersList) {
            membersList.innerHTML = (group.members || []).map(m => `
                <div class="member-item">
                    <span>${esc(m.name)}</span>
                    <span class="badge">${m.id === group.created_by ? 'Creator' : 'Member'}</span>
                </div>
            `).join('');
        }

        // Group balances
        try {
            const balances = await apiGet(`/api/balances/group/${groupId}`);
            const balDiv = document.getElementById('gd-balances');
            if (balDiv) {
                balDiv.innerHTML = !balances.length
                    ? '<p class="empty-state">✅ All clear! No debts.</p>'
                    : balances.map(b => `
                        <div class="balance-item">
                            <div class="balance-name">${esc(b.debtor_name)} owes ${esc(b.creditor_name)}</div>
                            <div class="balance-amount owes">${b.amount.toFixed(2)} ₽</div>
                        </div>
                    `).join('');
            }
        } catch (e) {
            const balDiv = document.getElementById('gd-balances');
            if (balDiv) balDiv.innerHTML = `<p class="empty-state">Error: ${esc(e.message)}</p>`;
        }

        // Group expenses
        try {
            const expenses = await apiGet(`/api/expenses?group_id=${groupId}&limit=50`);
            renderExpensesInContainer(expenses, 'gd-expenses');
        } catch (e) {
            const expDiv = document.getElementById('gd-expenses');
            if (expDiv) expDiv.innerHTML = `<p class="empty-state">Error: ${esc(e.message)}</p>`;
        }
    } catch (err) {
        showToast('Failed to load group: ' + err.message, 'error');
    }
}

document.getElementById('group-back-btn')?.addEventListener('click', () => {
    document.getElementById('group-detail').classList.add('hidden');
    document.getElementById('groups-list').classList.remove('hidden');
    const h2 = document.getElementById('create-group-form')?.parentElement?.querySelector('h2');
    if (h2) h2.classList.remove('hidden');
    document.getElementById('create-group-form')?.classList.remove('hidden');
});

function setupGroupForm() {
    document.getElementById('create-group-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('cg-name').value.trim();
        const description = document.getElementById('cg-desc').value.trim();
        if (!name) { showToast('Enter a group name', 'error'); return; }
        try {
            await apiPost('/api/groups', { name, description });
            document.getElementById('cg-name').value = '';
            document.getElementById('cg-desc').value = '';
            await loadGroups();
            await loadStats();
            showToast('Group created!', 'success');
        } catch (err) {
            showToast(err.message, 'error');
        }
    });
}

// --- Stats ---
async function loadStats() {
    try {
        const stats = await apiGet('/api/stats');
        setEl('stat-users', stats.users);
        setEl('stat-groups', stats.groups);
        setEl('stat-expenses', stats.expenses);
        setEl('stat-total', `${stats.total_expenses.toFixed(2)} ₽`);
        setEl('stat-settled', `${stats.total_settled.toFixed(2)} ₽`);
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

function setEl(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

// --- Expenses ---
async function loadExpenses(filters = {}) {
    try {
        const params = new URLSearchParams({ limit: 100 });
        if (filters.group_id) params.set('group_id', filters.group_id);
        if (filters.category) params.set('category', filters.category);
        if (filters.date_from) params.set('date_from', filters.date_from);
        if (filters.date_to) params.set('date_to', filters.date_to);

        const expenses = await apiGet(`/api/expenses?${params}`);
        renderExpenses(expenses);
    } catch (e) {
        console.error('Failed to load expenses:', e);
        const c = document.getElementById('expenses-list');
        if (c) c.innerHTML = `<p class="empty-state">Error loading expenses: ${esc(e.message)}</p>`;
    }
}

function renderExpenses(expenses) {
    renderExpensesInContainer(expenses, 'expenses-list');
}

function renderExpensesInContainer(expenses, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!expenses || !expenses.length) {
        container.innerHTML = '<p class="empty-state">No expenses yet.</p>';
        return;
    }

    const catEmoji = { food:'🍔', transport:'🚗', housing:'🏠', entertainment:'🎬', utilities:'💡', groceries:'🛒', other:'📦' };

    container.innerHTML = expenses.map(e => `
        <div class="expense-item">
            <div class="expense-info">
                <div class="expense-desc">${esc(e.description || 'No description')}</div>
                <div class="expense-meta">
                    Paid by <strong>${esc(e.payer_name)}</strong>
                    · ${formatDate(e.expense_date || e.created_at)}
                    · Split with ${(e.splits || []).length} people
                    <span class="expense-category">${catEmoji[e.category] || '📦'} ${e.category}</span>
                </div>
            </div>
            <div class="expense-amount">${e.amount.toFixed(2)} ${e.currency || '₽'}</div>
        </div>
    `).join('');
}

// --- Quick Expense ---
function updateQuickExpenseParticipants() {
    const container = document.getElementById('qe-participants');
    const payerId = parseInt(document.getElementById('qe-payer')?.value || 0);
    if (!container) return;

    let html = '<p class="hint">Split with:</p>';
    users.forEach(u => {
        if (u.id === payerId) return;
        html += `<label class="participant-checkbox">
            <input type="checkbox" value="${u.id}" checked> ${esc(u.name)}
        </label>`;
    });
    container.innerHTML = html;
}

document.getElementById('qe-payer')?.addEventListener('change', updateQuickExpenseParticipants);

// --- Balances Tab ---
async function loadBalancesTab() {
    const container = document.getElementById('balances-list');
    if (container) container.innerHTML = '<p class="empty-state">Select a user above</p>';
    const tb = document.getElementById('total-balance');
    if (tb) tb.innerHTML = '<p class="empty-state">Select a user to see total balance</p>';
}

document.getElementById('balance-user')?.addEventListener('change', async (e) => {
    const userId = parseInt(e.target.value);
    if (!userId) {
        loadBalancesTab();
        return;
    }

    const container = document.getElementById('balances-list');
    if (container) container.innerHTML = '<p class="empty-state">Loading...</p>';

    try {
        const groupId = document.getElementById('balance-group')?.value || null;
        const url = groupId ? `/api/balances/${userId}?group_id=${groupId}` : `/api/balances/${userId}`;
        const balances = await apiGet(url);

        if (container) {
            container.innerHTML = !balances.length
                ? '<p class="empty-state">✅ All clear! No debts.</p>'
                : balances.map(b => {
                    const isOwed = b.amount > 0;
                    const cls = isOwed ? 'owed' : 'owes';
                    const label = isOwed ? 'is owed to you' : 'you owe';
                    return `<div class="balance-item">
                        <div class="balance-name">${esc(b.user_name)} <span class="balance-label">${label}</span></div>
                        <div class="balance-amount ${cls}">${Math.abs(b.amount).toFixed(2)} ₽</div>
                    </div>`;
                }).join('');
        }

        // Total balance
        const total = await apiGet(`/api/balances/total/${userId}`);
        const tb = document.getElementById('total-balance');
        if (tb) {
            tb.innerHTML = `
                <div class="stat-row"><span>People owe you:</span><span class="owed">${total.total_owed.toFixed(2)} ₽</span></div>
                <div class="stat-row"><span>You owe:</span><span class="owes">${total.total_owes.toFixed(2)} ₽</span></div>
                <div class="stat-row"><span>Net:</span><span class="${total.net >= 0 ? 'owed' : 'owes'}">${total.net.toFixed(2)} ₽</span></div>
            `;
        }
    } catch (err) {
        const container = document.getElementById('balances-list');
        if (container) container.innerHTML = `<p class="empty-state">Error: ${esc(err.message)}</p>`;
    }
});

document.getElementById('balance-group')?.addEventListener('change', () => {
    const userId = parseInt(document.getElementById('balance-user')?.value || 0);
    if (userId) document.getElementById('balance-user')?.dispatchEvent(new Event('change'));
});

// --- Forms (Settle, Expense) ---
function setupForms() {
    // Quick expense form
    document.getElementById('quick-expense-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const resultDiv = document.getElementById('qe-result');
        if (resultDiv) resultDiv.classList.add('hidden');

        const payerId = parseInt(document.getElementById('qe-payer')?.value || 0);
        const amount = parseFloat(document.getElementById('qe-amount')?.value || 0);
        const description = document.getElementById('qe-desc')?.value?.trim();
        const category = document.getElementById('qe-category')?.value || 'other';
        const currency = document.getElementById('qe-currency')?.value || 'RUB';
        const splitType = document.getElementById('qe-split-type')?.value || 'equal';
        const groupId = document.getElementById('qe-group')?.value || null;

        const participantIds = [];
        document.querySelectorAll('#qe-participants input[type="checkbox"]:checked').forEach(cb => {
            participantIds.push(parseInt(cb.value));
        });

        if (!payerId) { showToast('Select who paid', 'error'); return; }
        if (!amount || amount <= 0) { showToast('Enter a valid amount', 'error'); return; }
        if (!participantIds.length) { showToast('Select at least one participant', 'error'); return; }

        const data = {
            payer_id: payerId, amount, participant_ids: participantIds,
            description: description || null, category, currency, split_type: splitType,
        };
        if (groupId) data.group_id = parseInt(groupId);

        try {
            const result = await apiPost('/api/expenses', data);
            if (resultDiv) {
                resultDiv.textContent = `✅ Added! ${result.payer_name} paid ${result.amount.toFixed(2)} ${result.currency} split ${(result.splits || []).length} ways.`;
                resultDiv.className = 'result success';
                resultDiv.classList.remove('hidden');
            }
            document.getElementById('qe-amount').value = '';
            document.getElementById('qe-desc').value = '';
            await Promise.allSettled([loadExpenses(), loadStats()]);
            showToast('Expense added!', 'success');
        } catch (err) {
            if (resultDiv) {
                resultDiv.textContent = `❌ ${err.message}`;
                resultDiv.className = 'result error';
                resultDiv.classList.remove('hidden');
            }
            showToast(err.message, 'error');
        }
    });

    // Settle form
    document.getElementById('settle-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const resultDiv = document.getElementById('settle-result');
        if (resultDiv) resultDiv.classList.add('hidden');

        const payerId = parseInt(document.getElementById('settle-payer')?.value || 0);
        const creditorId = parseInt(document.getElementById('settle-creditor')?.value || 0);
        const amountVal = document.getElementById('settle-amount')?.value;
        const amount = amountVal ? parseFloat(amountVal) : null;
        const groupId = document.getElementById('settle-group')?.value || null;

        if (!payerId) { showToast('Select who is paying', 'error'); return; }
        if (!creditorId) { showToast('Select who is receiving', 'error'); return; }
        if (payerId === creditorId) { showToast('Can\'t pay yourself', 'error'); return; }

        const data = { payer_id: payerId, creditor_id: creditorId, amount };
        if (groupId) data.group_id = parseInt(groupId);

        try {
            const result = await apiPost('/api/settle', data);
            if (resultDiv) {
                resultDiv.textContent = result.success ? `✅ ${result.message}` : `❌ ${result.message}`;
                resultDiv.className = `result ${result.success ? 'success' : 'error'}`;
                resultDiv.classList.remove('hidden');
            }
            if (result.success) {
                document.getElementById('settle-amount').value = '';
                await Promise.allSettled([loadStats(), loadSettlements()]);
                showToast('Settlement recorded!', 'success');
            } else {
                showToast(result.message, 'error');
            }
        } catch (err) {
            if (resultDiv) {
                resultDiv.textContent = `❌ ${err.message}`;
                resultDiv.className = 'result error';
                resultDiv.classList.remove('hidden');
            }
            showToast(err.message, 'error');
        }
    });

    // Expense filters
    document.getElementById('exp-apply-filters')?.addEventListener('click', () => {
        loadExpenses({
            group_id: document.getElementById('exp-group-filter')?.value || null,
            category: document.getElementById('exp-category-filter')?.value || null,
            date_from: document.getElementById('exp-date-from')?.value || null,
            date_to: document.getElementById('exp-date-to')?.value || null,
        });
    });
}

// --- Settlements ---
async function loadSettlements() {
    try {
        const settlements = await apiGet('/api/settlements?limit=50');
        const container = document.getElementById('settlements-list');
        if (!container) return;
        if (!settlements.length) {
            container.innerHTML = '<p class="empty-state">No settlements yet</p>';
            return;
        }
        container.innerHTML = settlements.map(s => {
            const payer = users.find(u => u.id === s.payer_id);
            const creditor = users.find(u => u.id === s.creditor_id);
            return `<div class="balance-item">
                <div class="balance-name">${esc(payer?.name || 'Unknown')} → ${esc(creditor?.name || 'Unknown')}</div>
                <div class="balance-amount owed">${s.amount.toFixed(2)} ${s.currency || '₽'}</div>
            </div>`;
        }).join('');
    } catch (e) {
        console.error('Failed to load settlements:', e);
        const container = document.getElementById('settlements-list');
        if (container) container.innerHTML = `<p class="empty-state">Error loading settlements</p>`;
    }
}

// --- Optimize ---
function setupOptimizeButton() {
    document.getElementById('optimize-btn')?.addEventListener('click', async () => {
        const resultDiv = document.getElementById('optimize-result');
        if (!resultDiv) return;
        resultDiv.innerHTML = '<p class="empty-state">Calculating...</p>';

        try {
            const groupId = document.getElementById('optimize-group')?.value || null;
            const url = groupId ? `/api/optimize-settlements?group_id=${groupId}` : '/api/optimize-settlements';
            const plan = await apiGet(url);

            if (!plan.length) {
                resultDiv.innerHTML = '<p class="empty-state">✅ No debts to settle!</p>';
                return;
            }

            resultDiv.innerHTML = plan.map(p => `
                <div class="optimize-item">
                    <div>
                        <span class="optimize-arrow">${esc(p.from_user_name)}</span>
                        <span class="optimize-arrow">→</span>
                        <span class="optimize-arrow">${esc(p.to_user_name)}</span>
                    </div>
                    <div class="expense-amount">${p.amount.toFixed(2)} ₽</div>
                </div>
            `).join('');
        } catch (err) {
            resultDiv.innerHTML = `<p class="empty-state">Error: ${esc(err.message)}</p>`;
        }
    });
}

// --- Utils ---
function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDate(str) {
    if (!str) return '';
    try {
        const d = new Date(str);
        return d.toLocaleDateString('en-GB', { day:'2-digit', month:'2-digit', year:'numeric' })
            + ' ' + d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' });
    } catch { return str; }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => { toast.className = 'toast hidden'; }, 3000);
}
