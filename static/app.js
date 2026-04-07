/* CashFlow — Web App JavaScript (Complete) */

const API = window.location.origin;

// State
let users = [];
let groups = [];
let currentUser = null;

// --- Init ---
document.addEventListener('DOMContentLoaded', async () => {
    // Check if user is logged in (simple session via localStorage)
    const savedUser = localStorage.getItem('cashflow_user');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        showApp();
    } else {
        showAuth();
    }

    setupAuthForms();
    setupTabs();
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
    await loadUsers();
    await loadGroups();
    await loadStats();
    await loadExpenses();
    await loadSettlements();
    setupForms();
    setupGroupForm();
    setupOptimizeButton();
}

function setupAuthForms() {
    // Toggle login/register
    document.getElementById('show-register').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-form').classList.remove('hidden');
    });

    document.getElementById('show-login').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('register-form').classList.add('hidden');
        document.getElementById('login-form').classList.remove('hidden');
    });

    // Demo access
    document.getElementById('demo-link').addEventListener('click', (e) => {
        e.preventDefault();
        currentUser = { id: 0, name: 'Demo User' };
        showApp();
    });

    // Sign in
    document.getElementById('signin-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        try {
            const user = await apiPost('/api/auth/login', { email, password });
            currentUser = user;
            localStorage.setItem('cashflow_user', JSON.stringify(user));
            showApp();
            showToast('Signed in!', 'success');
        } catch (err) {
            showToast(err.message || 'Login failed', 'error');
        }
    });

    // Sign up
    document.getElementById('signup-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('reg-name').value;
        const username = document.getElementById('reg-username').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;

        try {
            const user = await apiPost('/api/auth/register', { name, username, email, password });
            currentUser = user;
            localStorage.setItem('cashflow_user', JSON.stringify(user));
            showApp();
            showToast('Account created!', 'success');
        } catch (err) {
            showToast(err.message || 'Registration failed', 'error');
        }
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', () => {
        currentUser = null;
        localStorage.removeItem('cashflow_user');
        showAuth();
    });
}

// --- Tabs ---
function setupTabs() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');

            if (btn.dataset.tab === 'balances') loadBalancesTab();
            if (btn.dataset.tab === 'settle') loadSettlements();
        });
    });
}

// --- API Helpers ---
async function apiGet(url) {
    const res = await fetch(`${API}${url}`);
    if (!res.ok) throw new Error(`GET ${url}: ${res.status}`);
    return res.json();
}

async function apiPost(url, data) {
    const res = await fetch(`${API}${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || `POST ${url}: ${res.status}`);
    }
    return res.json();
}

async function apiPut(url, data) {
    const res = await fetch(`${API}${url}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || `PUT ${url}: ${res.status}`);
    }
    return res.json();
}

async function apiDelete(url) {
    const res = await fetch(`${API}${url}`, { method: 'DELETE' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || `DELETE ${url}: ${res.status}`);
    }
    return res.json();
}

// --- Users ---
async function loadUsers() {
    try {
        users = await apiGet('/api/users');
        populateUserSelects();
    } catch (e) {
        console.error('Failed to load users:', e);
    }
}

function populateUserSelects() {
    const selects = ['qe-payer', 'balance-user', 'settle-payer', 'settle-creditor', 'exp-user-filter'];
    selects.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const firstOption = el.querySelector('option');
        el.innerHTML = '';
        if (firstOption) el.appendChild(firstOption.cloneNode(true));
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
        // Load groups for first user (in production, would use current user's ID)
        const userId = users.length > 0 ? users[0].id : 0;
        groups = await apiGet(`/api/groups?user_id=${userId}`);
        populateGroupSelects();
        renderGroups();
    } catch (e) {
        console.error('Failed to load groups:', e);
    }
}

function populateGroupSelects() {
    const selects = ['qe-group', 'exp-group-filter', 'balance-group', 'settle-group', 'optimize-group'];
    selects.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const firstOption = el.querySelector('option');
        el.innerHTML = '';
        if (firstOption) el.appendChild(firstOption.cloneNode(true));
        groups.filter(g => !g.is_archived).forEach(g => {
            const opt = document.createElement('option');
            opt.value = g.id;
            opt.textContent = g.name;
            el.appendChild(opt);
        });
    });
}

function renderGroups() {
    const container = document.getElementById('groups-list');
    if (!groups.length) {
        container.innerHTML = '<p class="empty-state">No groups yet. Create your first group!</p>';
        return;
    }

    container.innerHTML = groups.map(g => `
        <div class="group-item" data-group-id="${g.id}">
            <div class="group-info">
                <div class="group-name">${esc(g.name)}</div>
                <div class="group-desc-text">${esc(g.description || '')}</div>
                <div class="group-meta">${g.member_count} members</div>
            </div>
            ${g.is_archived ? '<span class="badge badge-archived">Archived</span>' : ''}
        </div>
    `).join('');

    // Add click handlers
    container.querySelectorAll('.group-item').forEach(el => {
        el.addEventListener('click', () => openGroupDetail(parseInt(el.dataset.groupId)));
    });
}

async function openGroupDetail(groupId) {
    try {
        const group = await apiGet(`/api/groups/${groupId}`);
        document.getElementById('groups-list').classList.add('hidden');
        document.getElementById('create-group-form').parentElement.querySelector('h2').classList.add('hidden');
        document.getElementById('create-group-form').classList.add('hidden');

        const detail = document.getElementById('group-detail');
        detail.classList.remove('hidden');

        document.getElementById('gd-name').textContent = group.name;
        document.getElementById('gd-desc').textContent = group.description || 'No description';
        document.getElementById('gd-members').textContent = `${group.members.length} members`;

        const archivedBadge = document.getElementById('gd-archived');
        if (group.is_archived) {
            archivedBadge.classList.remove('hidden');
        } else {
            archivedBadge.classList.add('hidden');
        }

        // Members
        const membersList = document.getElementById('gd-members-list');
        membersList.innerHTML = group.members.map(m => `
            <div class="member-item">
                <span>${esc(m.name)}</span>
                <span class="badge">${m.id === group.created_by ? 'Creator' : 'Member'}</span>
            </div>
        `).join('');

        // Group balances
        const balances = await apiGet(`/api/balances/group/${groupId}`);
        const balancesDiv = document.getElementById('gd-balances');
        if (!balances.length) {
            balancesDiv.innerHTML = '<p class="empty-state">✅ All clear! No debts.</p>';
        } else {
            balancesDiv.innerHTML = balances.map(b => `
                <div class="balance-item">
                    <div class="balance-name">${esc(b.debtor_name)} owes ${esc(b.creditor_name)}</div>
                    <div class="balance-amount owes">${b.amount.toFixed(2)} ₽</div>
                </div>
            `).join('');
        }

        // Group expenses
        const expenses = await apiGet(`/api/expenses?group_id=${groupId}&limit=50`);
        renderExpensesInContainer(expenses, 'gd-expenses');

    } catch (err) {
        showToast('Failed to load group: ' + err.message, 'error');
    }
}

document.getElementById('group-back-btn').addEventListener('click', () => {
    document.getElementById('group-detail').classList.add('hidden');
    document.getElementById('groups-list').classList.remove('hidden');
    document.getElementById('create-group-form').parentElement.querySelector('h2').classList.remove('hidden');
    document.getElementById('create-group-form').classList.remove('hidden');
});

function setupGroupForm() {
    document.getElementById('create-group-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('cg-name').value.trim();
        const description = document.getElementById('cg-desc').value.trim();

        if (!name) { showToast('Enter a group name', 'error'); return; }

        try {
            const creatorId = users.length > 0 ? users[0].id : 1;
            await apiPost(`/api/groups?creator_id=${creatorId}`, { name, description });
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
        document.getElementById('stat-users').textContent = stats.users;
        document.getElementById('stat-groups').textContent = stats.groups;
        document.getElementById('stat-expenses').textContent = stats.expenses;
        document.getElementById('stat-total').textContent = `${stats.total_expenses.toFixed(2)} ₽`;
        document.getElementById('stat-settled').textContent = `${stats.total_settled.toFixed(2)} ₽`;
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

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
    }
}

function renderExpenses(expenses) {
    renderExpensesInContainer(expenses, 'expenses-list');
}

function renderExpensesInContainer(expenses, containerId) {
    const container = document.getElementById(containerId);
    if (!expenses.length) {
        container.innerHTML = '<p class="empty-state">No expenses yet.</p>';
        return;
    }

    const categoryEmojis = {
        food: '🍔', transport: '🚗', housing: '🏠', entertainment: '🎬',
        utilities: '💡', groceries: '🛒', other: '📦'
    };

    container.innerHTML = expenses.map(e => `
        <div class="expense-item">
            <div class="expense-info">
                <div class="expense-desc">${esc(e.description || 'No description')}</div>
                <div class="expense-meta">
                    Paid by <strong>${esc(e.payer_name)}</strong>
                    · ${formatDate(e.expense_date || e.created_at)}
                    · Split with ${(e.splits || []).length} people
                    <span class="expense-category">${categoryEmojis[e.category] || '📦'} ${e.category}</span>
                </div>
            </div>
            <div class="expense-amount">${e.amount.toFixed(2)} ${e.currency || '₽'}</div>
        </div>
    `).join('');
}

// --- Quick Expense ---
function updateQuickExpenseParticipants() {
    const container = document.getElementById('qe-participants');
    const payerSelect = document.getElementById('qe-payer');
    const payerId = parseInt(payerSelect.value);

    let html = '<p class="hint">Split with:</p>';
    users.forEach(u => {
        if (u.id === payerId) return;
        html += `
            <label class="participant-checkbox">
                <input type="checkbox" value="${u.id}" checked> ${esc(u.name)}
            </label>
        `;
    });
    container.innerHTML = html;
}

document.getElementById('qe-payer')?.addEventListener('change', updateQuickExpenseParticipants);

// --- Balances Tab ---
async function loadBalancesTab() {
    // Reset
    const container = document.getElementById('balances-list');
    container.innerHTML = '<p class="empty-state">Select a user above</p>';
    document.getElementById('total-balance').innerHTML = '<p class="empty-state">Select a user to see total balance</p>';
}

document.getElementById('balance-user')?.addEventListener('change', async (e) => {
    const userId = parseInt(e.target.value);
    if (!userId) {
        document.getElementById('balances-list').innerHTML = '<p class="empty-state">Select a user above</p>';
        document.getElementById('total-balance').innerHTML = '<p class="empty-state">Select a user to see total balance</p>';
        return;
    }

    const container = document.getElementById('balances-list');
    container.innerHTML = '<p class="empty-state">Loading...</p>';

    try {
        const groupId = document.getElementById('balance-group').value || null;
        const url = groupId
            ? `/api/balances/${userId}?group_id=${groupId}`
            : `/api/balances/${userId}`;
        const balances = await apiGet(url);

        if (!balances.length) {
            container.innerHTML = '<p class="empty-state">✅ All clear! No debts.</p>';
        } else {
            container.innerHTML = balances.map(b => {
                const isOwed = b.amount > 0;
                const cls = isOwed ? 'owed' : 'owes';
                const label = isOwed ? 'is owed to you' : 'you owe';
                return `
                    <div class="balance-item">
                        <div class="balance-name">${esc(b.user_name)} <span class="balance-label">${label}</span></div>
                        <div class="balance-amount ${cls}">${Math.abs(b.amount).toFixed(2)} ₽</div>
                    </div>
                `;
            }).join('');
        }

        // Total balance
        const total = await apiGet(`/api/balances/total/${userId}`);
        document.getElementById('total-balance').innerHTML = `
            <div class="stat-row"><span>People owe you:</span><span class="owed">${total.total_owed.toFixed(2)} ₽</span></div>
            <div class="stat-row"><span>You owe:</span><span class="owes">${total.total_owes.toFixed(2)} ₽</span></div>
            <div class="stat-row"><span>Net:</span><span class="${total.net >= 0 ? 'owed' : 'owes'}">${total.net.toFixed(2)} ₽</span></div>
        `;
    } catch (err) {
        container.innerHTML = `<p class="empty-state">Error: ${esc(err.message)}</p>`;
    }
});

document.getElementById('balance-group')?.addEventListener('change', () => {
    const userId = parseInt(document.getElementById('balance-user').value);
    if (userId) {
        document.getElementById('balance-user').dispatchEvent(new Event('change'));
    }
});

// --- Settle ---
function setupForms() {
    // Quick expense form
    document.getElementById('quick-expense-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const resultDiv = document.getElementById('qe-result');
        resultDiv.classList.add('hidden');

        const payerId = parseInt(document.getElementById('qe-payer').value);
        const amount = parseFloat(document.getElementById('qe-amount').value);
        const description = document.getElementById('qe-desc').value.trim();
        const category = document.getElementById('qe-category').value;
        const currency = document.getElementById('qe-currency').value;
        const splitType = document.getElementById('qe-split-type').value;
        const groupId = document.getElementById('qe-group').value || null;
        const participantIds = [];
        document.querySelectorAll('#qe-participants input[type="checkbox"]:checked').forEach(cb => {
            participantIds.push(parseInt(cb.value));
        });

        if (!payerId) { showToast('Select who paid', 'error'); return; }
        if (!amount || amount <= 0) { showToast('Enter a valid amount', 'error'); return; }
        if (!participantIds.length) { showToast('Select at least one participant', 'error'); return; }

        const data = {
            payer_id: payerId,
            amount,
            participant_ids: participantIds,
            description: description || null,
            category,
            currency,
            split_type: splitType,
        };
        if (groupId) data.group_id = parseInt(groupId);

        try {
            const result = await apiPost('/api/expenses', data);

            resultDiv.textContent = `✅ Added! ${result.payer_name} paid ${result.amount.toFixed(2)} ${result.currency} split ${(result.splits || []).length} ways.`;
            resultDiv.className = 'result success';
            resultDiv.classList.remove('hidden');

            document.getElementById('qe-amount').value = '';
            document.getElementById('qe-desc').value = '';
            await Promise.all([loadExpenses(), loadStats()]);
            showToast('Expense added!', 'success');
        } catch (err) {
            resultDiv.textContent = `❌ ${err.message}`;
            resultDiv.className = 'result error';
            resultDiv.classList.remove('hidden');
            showToast(err.message, 'error');
        }
    });

    // Settle form
    document.getElementById('settle-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const resultDiv = document.getElementById('settle-result');
        resultDiv.classList.add('hidden');

        const payerId = parseInt(document.getElementById('settle-payer').value);
        const creditorId = parseInt(document.getElementById('settle-creditor').value);
        const amountVal = document.getElementById('settle-amount').value;
        const amount = amountVal ? parseFloat(amountVal) : null;
        const groupId = document.getElementById('settle-group').value || null;

        if (!payerId) { showToast('Select who is paying', 'error'); return; }
        if (!creditorId) { showToast('Select who is receiving', 'error'); return; }
        if (payerId === creditorId) { showToast('Can\'t pay yourself', 'error'); return; }

        const data = { payer_id: payerId, creditor_id: creditorId, amount };
        if (groupId) data.group_id = parseInt(groupId);

        try {
            const result = await apiPost('/api/settle', data);

            resultDiv.textContent = result.success ? `✅ ${result.message}` : `❌ ${result.message}`;
            resultDiv.className = `result ${result.success ? 'success' : 'error'}`;
            resultDiv.classList.remove('hidden');

            if (result.success) {
                document.getElementById('settle-amount').value = '';
                await Promise.all([loadStats(), loadSettlements()]);
                showToast('Settlement recorded!', 'success');
            } else {
                showToast(result.message, 'error');
            }
        } catch (err) {
            resultDiv.textContent = `❌ ${err.message}`;
            resultDiv.className = 'result error';
            resultDiv.classList.remove('hidden');
            showToast(err.message, 'error');
        }
    });

    // Expense filters
    document.getElementById('exp-apply-filters').addEventListener('click', () => {
        const filters = {
            group_id: document.getElementById('exp-group-filter').value || null,
            category: document.getElementById('exp-category-filter').value || null,
            date_from: document.getElementById('exp-date-from').value || null,
            date_to: document.getElementById('exp-date-to').value || null,
        };
        loadExpenses(filters);
    });
}

// --- Settlements ---
async function loadSettlements() {
    try {
        const settlements = await apiGet('/api/settlements?limit=50');
        const container = document.getElementById('settlements-list');
        if (!settlements.length) {
            container.innerHTML = '<p class="empty-state">No settlements yet</p>';
            return;
        }

        container.innerHTML = settlements.map(s => {
            const payer = users.find(u => u.id === s.payer_id);
            const creditor = users.find(u => u.id === s.creditor_id);
            return `
                <div class="balance-item">
                    <div class="balance-name">${esc(payer?.name || 'Unknown')} → ${esc(creditor?.name || 'Unknown')}</div>
                    <div class="balance-amount owed">${s.amount.toFixed(2)} ${s.currency || '₽'}</div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Failed to load settlements:', e);
    }
}

// --- Optimize ---
function setupOptimizeButton() {
    document.getElementById('optimize-btn').addEventListener('click', async () => {
        const resultDiv = document.getElementById('optimize-result');
        resultDiv.innerHTML = '<p class="empty-state">Calculating...</p>';

        try {
            const groupId = document.getElementById('optimize-group').value || null;
            const url = groupId
                ? `/api/optimize-settlements?group_id=${groupId}`
                : '/api/optimize-settlements';
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
        return d.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' })
            + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    } catch { return str; }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => { toast.className = 'toast hidden'; }, 3000);
}
