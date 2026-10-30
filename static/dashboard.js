// Personal Finance & Budget Dashboard
// Stefan: base page interactions, Excel import/export, Flask connection.
// Eli: calculations integration, visualizations, persistence, editing, dates,
// custom categories, savings goal, currency converter, and final integration.

let transactions = [];
let budget = '0';
let savingsGoal = '0';
let savingsSaved = '0';
let editingIndex = null;
let tipTimer = null;
let statusTimer = null;

const STORAGE_KEY = 'balance-dashboard-state-v2';
const DEFAULT_CATEGORIES = ['Housing', 'Food', 'Transport', 'Entertainment', 'Utilities', 'Other'];
const element = id => document.getElementById(id);
const dollars = value => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(Number(value || 0));
const percent = value => value === null || value === undefined ? 'N/A' : `${Number(value).toFixed(1)}%`;

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function titleCase(value) {
  const text = String(value || '');
  return text ? text.charAt(0).toUpperCase() + text.slice(1).toLowerCase() : '';
}

function message(text, error = false, keep = false) {
  const box = element('status');
  if (statusTimer) clearTimeout(statusTimer);
  box.textContent = text;
  box.classList.toggle('error', error);
  box.classList.toggle('success', !error);
  box.hidden = !text;
  if (text && !keep) {
    statusTimer = setTimeout(() => { box.hidden = true; }, 5000);
  }
}

function markInvalid(field, text) {
  document.querySelectorAll('.field-error').forEach(item => item.classList.remove('field-error'));
  field.classList.add('field-error');
  field.focus();
  message(text, true, true);
}

function clearInvalid() {
  document.querySelectorAll('.field-error').forEach(item => item.classList.remove('field-error'));
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    transactions,
    budget,
    savingsGoal,
    savingsSaved
  }));
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (!saved || typeof saved !== 'object') return false;
    transactions = Array.isArray(saved.transactions) ? saved.transactions : [];
    budget = String(saved.budget ?? '0');
    savingsGoal = String(saved.savingsGoal ?? '0');
    savingsSaved = String(saved.savingsSaved ?? '0');
    return true;
  } catch (_) {
    return false;
  }
}

function categoryValue() {
  if (element('category').value === '__custom__') {
    return element('custom-category').value.trim();
  }
  return element('category').value;
}

function syncCategoryInput() {
  const custom = element('category').value === '__custom__';
  element('custom-category').hidden = !custom;
  if (custom) element('custom-category').focus();
}

function setCategoryForEdit(category) {
  if (DEFAULT_CATEGORIES.includes(category)) {
    element('category').value = category;
    element('custom-category').hidden = true;
    element('custom-category').value = '';
  } else {
    element('category').value = '__custom__';
    element('custom-category').hidden = false;
    element('custom-category').value = category;
  }
}

function resetTransactionForm() {
  editingIndex = null;
  element('transaction-heading').textContent = 'Add a transaction';
  element('edit-badge').hidden = true;
  element('transaction-submit').textContent = 'Add transaction';
  element('cancel-edit').hidden = true;
  element('type').value = 'expense';
  element('transaction-date').value = todayISO();
  element('description').value = '';
  element('amount').value = '';
  element('category').value = 'Housing';
  element('custom-category').value = '';
  element('custom-category').hidden = true;
  element('category').disabled = false;
  clearInvalid();
  element('type').focus();
}

function beginEdit(index) {
  const transaction = transactions[index];
  editingIndex = index;
  element('transaction-heading').textContent = 'Edit transaction';
  element('edit-badge').hidden = false;
  element('transaction-submit').textContent = 'Save changes';
  element('cancel-edit').hidden = false;
  element('type').value = transaction.type;
  element('transaction-date').value = transaction.date || '';
  element('description').value = transaction.description;
  element('amount').value = transaction.amount;
  setCategoryForEdit(transaction.category || 'Other');
  element('category').disabled = transaction.type === 'income';
  element('transaction-form').scrollIntoView({behavior: 'smooth', block: 'center'});
  element('type').focus();
}

function renderCashFlow(summary) {
  const chart = element('cash-flow-chart');
  chart.replaceChildren();
  const values = [['Income', summary.income], ['Expenses', summary.expenses], ['Remaining', summary.remaining]];
  const maxValue = Math.max(1, ...values.map(([, value]) => Math.abs(value)));

  for (const [labelText, value] of values) {
    const row = document.createElement('div'); row.className = 'flow-row';
    const label = document.createElement('div'); label.className = 'flow-label';
    const name = document.createElement('span'); name.textContent = labelText;
    const amount = document.createElement('strong'); amount.textContent = dollars(value);
    if (value < 0) amount.classList.add('negative');
    label.append(name, amount);
    const track = document.createElement('div'); track.className = 'flow-track';
    const bar = document.createElement('div');
    bar.className = `flow-bar flow-${labelText.toLowerCase()}`;
    if (value < 0) bar.classList.add('negative-bar');
    bar.style.width = `${Math.abs(value) / maxValue * 100}%`;
    track.append(bar); row.append(label, track); chart.append(row);
  }
}

function renderAllocation(summary) {
  const donut = element('allocation-donut');
  const spent = summary.expenses;
  const income = summary.income;
  const remaining = summary.remaining;
  element('allocation-spent').textContent = dollars(spent);
  element('allocation-remaining').textContent = dollars(remaining);
  element('allocation-remaining').classList.toggle('negative', remaining < 0);

  if (income <= 0) {
    donut.style.setProperty('--spent-percent', '0%');
    element('allocation-percent').textContent = 'N/A';
    element('allocation-note').textContent = 'Add income to calculate allocation.';
    return;
  }

  const spentPercent = spent / income * 100;
  donut.style.setProperty('--spent-percent', `${Math.min(Math.max(spentPercent, 0), 100)}%`);
  element('allocation-percent').textContent = `${spentPercent.toFixed(1)}%`;
  element('allocation-note').textContent = remaining < 0
    ? `Spending is ${dollars(Math.abs(remaining))} above income.`
    : `${dollars(remaining)} remains after expenses.`;
}

function renderTips(tips) {
  const tipList = Array.isArray(tips) && tips.length ? tips : [{
    message: 'Track income and expenses regularly to understand where your money is going.',
    source: 'Dashboard guidance', url: ''
  }];
  if (tipTimer) clearInterval(tipTimer);
  let index = 0;

  const showTip = () => {
    const tip = tipList[index];
    const track = element('tip-track');
    element('tip-text').textContent = tip.message;
    const source = element('tip-source');
    if (tip.url) {
      source.href = tip.url;
      source.textContent = `Source: ${tip.source} ↗`;
      source.hidden = false;
    } else source.hidden = true;
    track.classList.remove('ticker-move');
    void track.offsetWidth;
    track.classList.add('ticker-move');
    index = (index + 1) % tipList.length;
  };

  showTip();
  if (tipList.length > 1) tipTimer = setInterval(showTip, 11000);
}

function renderBudget(summary) {
  const used = summary.budget_used_percent;
  const status = element('budget-status');
  const bar = element('budget-progress-bar');
  element('budget-used').textContent = percent(used);
  element('income-spent').textContent = `Income spent: ${percent(summary.income_spent_percent)}`;
  status.textContent = summary.budget_message;
  status.className = '';

  if (summary.budget_status === 'not_set') {
    status.classList.add('budget-neutral');
    bar.style.width = '0%';
    bar.className = '';
  } else if (summary.budget_status === 'over') {
    status.classList.add('budget-over');
    bar.style.width = '100%';
    bar.className = 'over';
  } else {
    status.classList.add('budget-under');
    bar.style.width = `${Math.min(Math.max(used || 0, 0), 100)}%`;
    bar.className = used >= 80 ? 'warning' : '';
  }
}

function shareLabel(share) {
  if (share > 0 && share < 0.1) return '<0.1%';
  if (share < 1) return `${share.toFixed(2)}%`;
  return `${share.toFixed(1)}%`;
}

function renderCategoryChart(summary) {
  const chart = element('chart');
  chart.replaceChildren();
  if (!summary.expenses) {
    const note = document.createElement('p');
    note.className = 'muted';
    note.textContent = 'No spending yet. Your chart will appear after an expense is added.';
    chart.append(note);
    return;
  }

  const entries = Object.entries(summary.categories)
    .filter(([, total]) => Number(total) > 0)
    .sort((a, b) => b[1] - a[1]);

  for (const [category, total] of entries) {
    const share = Number(total) / summary.expenses * 100;
    const row = document.createElement('div'); row.className = 'chart-row';
    const label = document.createElement('div'); label.className = 'chart-label';
    const name = document.createElement('span'); name.textContent = category;
    const value = document.createElement('span'); value.className = 'chart-value';
    const amount = document.createElement('strong'); amount.textContent = dollars(total);
    const pill = document.createElement('span'); pill.className = 'percent-pill'; pill.textContent = shareLabel(share);
    if (share >= 50) pill.classList.add('share-large');
    else if (share >= 25) pill.classList.add('share-medium');
    value.append(amount, pill); label.append(name, value);

    const track = document.createElement('div'); track.className = 'track'; track.setAttribute('aria-hidden', 'true');
    const bar = document.createElement('div'); bar.className = 'bar';
    if (share >= 50) bar.classList.add('bar-large');
    else if (share >= 25) bar.classList.add('bar-medium');
    bar.style.width = `${Math.max(share, 0.6)}%`;
    track.append(bar); row.append(label, track); chart.append(row);
  }
}

function renderSavings() {
  const goal = Number(savingsGoal || 0);
  const saved = Number(savingsSaved || 0);
  element('savings-goal').value = savingsGoal;
  element('savings-saved').value = savingsSaved;

  if (goal <= 0) {
    element('savings-progress-bar').style.width = '0%';
    element('savings-percent').textContent = 'No goal set';
    element('savings-message').textContent = 'Set a savings goal to track progress.';
    return;
  }

  const progress = saved / goal * 100;
  element('savings-progress-bar').style.width = `${Math.min(progress, 100)}%`;
  element('savings-percent').textContent = `${progress.toFixed(1)}% complete`;
  const remaining = Math.max(goal - saved, 0);
  element('savings-message').textContent = remaining > 0
    ? `${dollars(remaining)} to go toward your ${dollars(goal)} goal.`
    : `Goal reached! You have saved ${dollars(saved)}.`;
}

function renderTransactions() {
  const body = element('transactions');
  body.replaceChildren();
  transactions.forEach((transaction, index) => {
    const row = document.createElement('tr');
    const values = [
      transaction.date || '—',
      transaction.description,
      titleCase(transaction.type),
      transaction.type === 'income' ? '—' : transaction.category,
      dollars(transaction.amount)
    ];
    values.forEach(value => { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); });

    const actions = document.createElement('td'); actions.className = 'row-actions';
    const edit = document.createElement('button'); edit.className = 'edit'; edit.textContent = 'Edit';
    edit.addEventListener('click', () => beginEdit(index));
    const remove = document.createElement('button'); remove.className = 'remove'; remove.textContent = 'Remove';
    remove.addEventListener('click', () => update(transactions.filter((_, i) => i !== index), budget, 'Transaction removed.'));
    actions.append(edit, remove); row.append(actions); body.append(row);
  });
  element('count').textContent = `${transactions.length} ${transactions.length === 1 ? 'ENTRY' : 'ENTRIES'}`;
  element('empty').hidden = transactions.length > 0;
}

function render(summary) {
  ['income', 'expenses', 'remaining'].forEach(key => element(key).textContent = dollars(summary[key]));
  element('remaining').classList.toggle('negative', summary.remaining < 0);
  renderBudget(summary);
  renderCashFlow(summary);
  renderAllocation(summary);
  renderTips(summary.tips);
  renderCategoryChart(summary);
  renderTransactions();
  renderSavings();
}

async function update(nextTransactions, nextBudget, successMessage = '') {
  document.querySelectorAll('button').forEach(button => button.disabled = true);
  clearInvalid();
  try {
    const response = await fetch('/api/summary', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({transactions: nextTransactions, budget: nextBudget, savings_goal: savingsGoal, savings_saved: savingsSaved})
    });
    const summary = await response.json();
    if (!response.ok) throw new Error(summary.error || 'Unable to calculate totals.');
    transactions = nextTransactions;
    budget = String(nextBudget);
    element('budget').value = budget;
    render(summary);
    saveState();
    if (successMessage) message(successMessage);
    return true;
  } catch (error) {
    message(`${error.message} Your last successful totals are unchanged.`, true, true);
    return false;
  } finally {
    document.querySelectorAll('button').forEach(button => button.disabled = false);
  }
}

function validateTransactionForm() {
  const description = element('description').value.trim();
  const amount = Number(element('amount').value);
  if (!description) { markInvalid(element('description'), 'Please enter a description.'); return null; }
  if (!element('amount').value || !Number.isFinite(amount) || amount <= 0) { markInvalid(element('amount'), 'Please enter an amount greater than $0.'); return null; }
  const category = categoryValue();
  if (element('type').value === 'expense' && !category) { markInvalid(element('custom-category'), 'Please enter a custom category name.'); return null; }
  return {
    date: element('transaction-date').value,
    description,
    type: element('type').value,
    amount: element('amount').value,
    category: element('type').value === 'income' ? 'Other' : category
  };
}

element('type').addEventListener('change', () => {
  const income = element('type').value === 'income';
  element('category').disabled = income;
  element('custom-category').disabled = income;
});
element('category').addEventListener('change', syncCategoryInput);
element('cancel-edit').addEventListener('click', resetTransactionForm);

element('transaction-form').addEventListener('submit', async event => {
  event.preventDefault();
  const transaction = validateTransactionForm();
  if (!transaction) return;
  const next = [...transactions];
  let text;
  if (editingIndex === null) {
    next.push(transaction); text = 'Transaction added.';
  } else {
    next[editingIndex] = transaction; text = 'Transaction updated.';
  }
  if (await update(next, budget, text)) resetTransactionForm();
});

element('budget-form').addEventListener('submit', async event => {
  event.preventDefault();
  const value = element('budget').value;
  if (value === '' || Number(value) < 0) return markInvalid(element('budget'), 'Budget must be $0 or greater.');
  await update(transactions, value, Number(value) === 0 ? 'Budget cleared.' : 'Monthly budget updated.');
});

element('savings-form').addEventListener('submit', event => {
  event.preventDefault();
  const goal = Number(element('savings-goal').value);
  const saved = Number(element('savings-saved').value);
  if (!Number.isFinite(goal) || goal < 0) return markInvalid(element('savings-goal'), 'Savings goal must be $0 or greater.');
  if (!Number.isFinite(saved) || saved < 0) return markInvalid(element('savings-saved'), 'Current savings must be $0 or greater.');
  savingsGoal = String(goal);
  savingsSaved = String(saved);
  renderSavings(); saveState(); message(goal > 0 ? 'Savings goal updated.' : 'Savings goal cleared.');
});

element('demo').addEventListener('click', () => {
  if (transactions.length && !window.confirm('Replace the current entries with the sample month?')) return;
  update([
    {date: todayISO(), description: 'Monthly pay', type: 'income', amount: '3000', category: 'Other'},
    {date: todayISO(), description: 'Rent', type: 'expense', amount: '1000', category: 'Housing'},
    {date: todayISO(), description: 'Groceries', type: 'expense', amount: '350', category: 'Food'},
    {date: todayISO(), description: 'Pet supplies', type: 'expense', amount: '45', category: 'Pets'},
    {date: todayISO(), description: 'Gas', type: 'expense', amount: '150', category: 'Transport'}
  ], '2000', 'Sample month loaded. These are fictional transactions.');
});

// Excel import/export
element('import').addEventListener('click', () => element('import-file').click());
element('import-file').addEventListener('change', async () => {
  const file = element('import-file').files[0]; element('import-file').value = '';
  if (!file) return;
  if (transactions.length && !window.confirm('Replace the current entries with the spreadsheet?')) return;
  message('Importing…', false, true);
  try {
    const form = new FormData(); form.append('file', file);
    const response = await fetch('/api/import', {method: 'POST', body: form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to import the spreadsheet.');
    savingsGoal = String(data.savings_goal ?? '0');
    savingsSaved = String(data.savings_saved ?? '0');
    await update(data.transactions, data.budget, `Imported ${data.transactions.length} transactions from ${file.name}.`);
  } catch (error) { message(`${error.message} Your current entries are unchanged.`, true, true); }
});

element('export').addEventListener('click', async () => {
  if (!transactions.length) return message('Add a transaction before exporting.', true, true);
  message('Preparing spreadsheet…', false, true);
  try {
    const response = await fetch('/api/export', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({transactions, budget, savings_goal: savingsGoal, savings_saved: savingsSaved})
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || 'Unable to export the spreadsheet.');
    }
    const name = response.headers.get('content-disposition')?.match(/filename="?([^";]+)"?/)?.[1] || 'budget.xlsx';
    const link = document.createElement('a');
    link.href = URL.createObjectURL(await response.blob()); link.download = name; link.click();
    URL.revokeObjectURL(link.href); message(`Exported ${transactions.length} transactions to ${name}.`);
  } catch (error) { message(error.message, true, true); }
});

element('clear-saved').addEventListener('click', async () => {
  if (!window.confirm('Clear all saved dashboard data from this browser?')) return;
  localStorage.removeItem(STORAGE_KEY);
  transactions = []; budget = '0'; savingsGoal = '0'; savingsSaved = '0';
  await update([], '0', 'Saved dashboard data cleared.');
  resetTransactionForm();
});

// Currency converter
element('converter-form').addEventListener('submit', async event => {
  event.preventDefault();
  const amountField = element('convert-amount');
  const amount = Number(amountField.value);
  if (!amountField.value || !Number.isFinite(amount) || amount < 0) return markInvalid(amountField, 'Enter a valid amount to convert.');
  element('converter-result').textContent = 'Converting…';
  try {
    const response = await fetch('/api/convert', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({amount, from: element('convert-from').value, to: element('convert-to').value})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to convert currency.');
    element('converter-result').innerHTML = `<strong>${Number(data.amount).toLocaleString(undefined, {maximumFractionDigits: 2})} ${data.from}</strong><span>=</span><strong>${Number(data.converted).toLocaleString(undefined, {maximumFractionDigits: 2})} ${data.to}</strong><small>Rate: 1 ${data.from} = ${Number(data.rate).toFixed(4)} ${data.to}${data.date ? ` · ${data.date}` : ''}</small>`;
  } catch (error) {
    element('converter-result').textContent = error.message;
    message(error.message, true, true);
  }
});

async function loadExchangeRates() {
  try {
    const response = await fetch('/api/exchange-rates');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to load exchange rates.');
    const container = element('exchange-rates'); container.replaceChildren();
    for (const currency of ['EUR', 'GBP', 'MXN', 'CAD', 'JPY']) {
      const card = document.createElement('article');
      const label = document.createElement('p'); label.textContent = `1 USD → ${currency}`;
      const value = document.createElement('strong'); value.textContent = data.rates[currency] !== undefined ? Number(data.rates[currency]).toFixed(4) : 'N/A';
      card.append(label, value); container.append(card);
    }
    element('exchange-date').textContent = data.date ? `Exchange-rate date: ${data.date} · Source: ${data.source}` : `Source: ${data.source}`;
  } catch (error) {
    element('exchange-rates').textContent = 'Exchange rates are temporarily unavailable.';
    element('exchange-date').textContent = '';
  }
}

// Startup
(async function start() {
  element('transaction-date').value = todayISO();
  const restored = loadState();
  element('budget').value = budget;
  element('savings-goal').value = savingsGoal;
  element('savings-saved').value = savingsSaved;
  await update(transactions, budget, restored ? 'Saved dashboard data restored.' : 'Ready. Add your first transaction or load a sample month.');
  loadExchangeRates();
})();
