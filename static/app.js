const $ = (selector) => document.querySelector(selector);

const state = {
  token: sessionStorage.getItem("spendwise-token"),
  user: null,
  categories: [],
  transactions: [],
  budgets: [],
  summaries: [],
};

let registering = false;
let editing = null;
let noticeTimer;
let loadVersion = 0;

function today() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

$("#view-month").value = today().slice(0, 7);

function notify(message, error = false) {
  const notice = $("#notice");
  notice.textContent = message;
  notice.classList.toggle("error", error);
  notice.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => {
    notice.hidden = true;
  }, 6000);
}

function setToken(token) {
  state.token = token;
  if (token) {
    sessionStorage.setItem("spendwise-token", token);
  } else {
    sessionStorage.removeItem("spendwise-token");
  }
}

function logout() {
  loadVersion += 1;
  setToken(null);
  state.user = null;
  state.categories = [];
  state.transactions = [];
  state.budgets = [];
  state.summaries = [];
  $("#editor").close();
  $("#app-view").hidden = true;
  $("#auth-view").hidden = false;
  $("#auth-form").reset();
  $("#transaction-rows").replaceChildren();
  $("#category-rows").replaceChildren();
  $("#budget-cards").replaceChildren();
}

async function api(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };

  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let message = data?.detail || `Request failed (${response.status})`;

    if (Array.isArray(message)) {
      message = message.map((item) => item.msg).join(". ");
    }

    if (response.status === 401 && state.token) {
      logout();
      message = "Your session expired. Please log in again.";
    }

    throw new Error(String(message));
  }

  return data;
}

// Work in cents when adding money to avoid floating-point rounding.
function cents(value) {
  const [whole, fraction = ""] = String(value).split(".");
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0").slice(0, 2));
}

function money(valueInCents) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(valueInCents / 100);
}

function categoryName(id) {
  return state.categories.find((category) => category.id === id)?.name
    || "Unknown category";
}

function categoryKind(id) {
  return state.categories.find((category) => category.id === id)?.kind;
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function actionButton(label, handler, className = "secondary") {
  const button = element("button", label, className);
  button.type = "button";
  button.addEventListener("click", handler);
  return button;
}

function addEmptyRow(container, columns, message) {
  const row = element("tr");
  const cell = element("td", message, "empty");
  cell.colSpan = columns;
  row.append(cell);
  container.append(row);
}

function recordActions(type, record) {
  const cell = element("td");
  cell.append(
    actionButton("Edit", () => openEditor(type, record)),
    actionButton("Delete", (event) => {
      removeRecord(type, record, event.currentTarget);
    }, "danger"),
  );
  return cell;
}

function render() {
  const month = $("#view-month").value;
  const transactions = state.transactions.filter(
    (transaction) => transaction.transaction_date.startsWith(month),
  );

  let income = 0;
  let expenses = 0;

  for (const transaction of transactions) {
    const amount = cents(transaction.amount);
    if (categoryKind(transaction.category_id) === "income") {
      income += amount;
    } else {
      expenses += amount;
    }
  }

  $("#income-total").textContent = money(income);
  $("#expense-total").textContent = money(expenses);
  $("#net-total").textContent = money(income - expenses);

  const transactionRows = $("#transaction-rows");
  transactionRows.replaceChildren();

  const sorted = [...transactions].sort(
    (a, b) => b.transaction_date.localeCompare(a.transaction_date) || b.id - a.id,
  );

  for (const transaction of sorted) {
    const row = element("tr");
    const incoming = categoryKind(transaction.category_id) === "income";

    row.append(
      element("td", transaction.transaction_date),
      element("td", transaction.description || "—"),
      element("td", categoryName(transaction.category_id)),
      element(
        "td",
        `${incoming ? "+" : "−"}${money(cents(transaction.amount))}`,
        incoming ? "money-in" : "money-out",
      ),
      recordActions("transaction", transaction),
    );

    transactionRows.append(row);
  }

  if (!sorted.length) {
    addEmptyRow(transactionRows, 5, "No transactions this month. Add your first one.");
  }

  const categoryRows = $("#category-rows");
  categoryRows.replaceChildren();

  for (const category of state.categories) {
    const row = element("tr");
    row.append(
      element("td", category.name),
      element("td", category.kind === "income" ? "Income" : "Expense"),
      recordActions("category", category),
    );
    categoryRows.append(row);
  }

  if (!state.categories.length) {
    addEmptyRow(categoryRows, 3, "Start with a category, such as Groceries or Salary.");
  }

  const budgetCards = $("#budget-cards");
  budgetCards.replaceChildren();

  for (const budget of state.budgets.filter(
    (item) => item.month.startsWith(month),
  )) {
    const summary = state.summaries.find(
      (item) => item.budget_id === budget.id,
    );

    const limit = cents(budget.monthly_limit);
    const spent = cents(summary.total_spent);
    const remaining = limit - spent;
    const card = element("article", undefined, "budget-card");
    const progress = element("progress");

    progress.max = limit;
    progress.value = Math.min(spent, limit);
    progress.setAttribute("aria-label", `${categoryName(budget.category_id)} spending`);

    const actions = element("div", undefined, "actions");
    actions.append(
      actionButton("Edit limit", () => openEditor("budget", budget)),
      actionButton("Delete", (event) => {
        removeRecord("budget", budget, event.currentTarget);
      }, "danger"),
    );

    card.append(
      element("h3", categoryName(budget.category_id)),
      element("p", `${money(spent)} spent of ${money(limit)}`, "muted"),
      progress,
      element(
        "p",
        remaining >= 0
          ? `${money(remaining)} remaining`
          : `${money(-remaining)} over budget`,
        remaining < 0 ? "money-out" : "money-in",
      ),
      actions,
    );

    budgetCards.append(card);
  }

  if (!budgetCards.children.length) {
    budgetCards.append(
      element("p", "No budgets for this month. Give your spending a plan.", "empty"),
    );
  }
}

// The API returns transactions in pages; load every page for accurate totals.
async function allTransactions() {
  const results = [];
  let offset = 0;

  while (true) {
    const page = await api(`/transactions?limit=100&offset=${offset}`);
    results.push(...page);
    if (page.length < 100) return results;
    offset += 100;
  }
}

async function loadData() {
  const version = ++loadVersion;

  const [categories, transactions, budgets] = await Promise.all([
    api("/categories"),
    allTransactions(),
    api("/budgets"),
  ]);

  const month = $("#view-month").value;
  const summaries = await Promise.all(
    budgets
      .filter((budget) => budget.month.startsWith(month))
      .map((budget) => api(`/budgets/${budget.id}/summary`)),
  );

  if (version !== loadVersion || !state.token) return;

  Object.assign(state, { categories, transactions, budgets, summaries });
  render();
}

async function enterApp() {
  state.user = await api("/auth/me");
  await loadData();
  if (!state.token) return;

  $("#user-name").textContent = state.user.name;
  $("#auth-view").hidden = true;
  $("#app-view").hidden = false;
}

$("#auth-toggle").addEventListener("click", () => {
  registering = !registering;

  $("#name-field").hidden = !registering;
  $("#name-field input").required = registering;
  $("#password-help").hidden = !registering;
  $("#auth-title").textContent = registering ? "A fresh start" : "Welcome back";
  $("#auth-subtitle").textContent = registering
    ? "Create your SpendWise account."
    : "Log in to see your overview.";
  $("#auth-submit").textContent = registering ? "Create account" : "Log in";
  $("#auth-toggle").textContent = registering
    ? "Already have an account? Log in"
    : "New here? Create an account";

  const password = $("#auth-form input[name=password]");
  password.autocomplete = registering ? "new-password" : "current-password";
  password.minLength = registering ? 15 : 1;
  if (registering) password.maxLength = 128;
  else password.removeAttribute("maxlength");
});

$("#auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const button = $("#auth-submit");
  const data = Object.fromEntries(new FormData(event.currentTarget));
  const wasRegistering = registering;
  button.disabled = true;
  $("#auth-toggle").disabled = true;

  try {
    if (wasRegistering) {
      await api("/auth/register", {
        method: "POST",
        body: { name: data.name, email: data.email, password: data.password },
      });
      notify("Account created. Logging you in.");
    }

    const result = await api("/auth/login", {
      method: "POST",
      body: { email: data.email, password: data.password },
    });

    setToken(result.access_token);
    await enterApp();
    $("#auth-form").reset();
  } catch (error) {
    notify(error.message, true);
  } finally {
    button.disabled = false;
    $("#auth-toggle").disabled = false;
  }
});

$("#logout").addEventListener("click", logout);

document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-tab]").forEach((tab) => {
      const active = tab === button;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-pressed", String(active));
      $(`#${tab.dataset.tab}-panel`).hidden = !active;
    });
  });
});

$("#view-month").addEventListener("change", async () => {
  if (!$("#view-month").value) return;
  try {
    await loadData();
  } catch (error) {
    notify(error.message, true);
  }
});

function inputField(name, title, type, value, attributes = {}) {
  const label = element("label", title);
  const input = element("input");
  input.name = name;
  input.type = type;
  input.value = value ?? "";

  for (const [key, attributeValue] of Object.entries(attributes)) {
    input.setAttribute(key, attributeValue);
  }

  label.append(input);
  $("#editor-fields").append(label);
  return input;
}

function selectField(name, title, options, value) {
  const label = element("label", title);
  const select = element("select");
  select.name = name;
  select.required = true;

  for (const [optionValue, text] of options) {
    const option = element("option", text);
    option.value = optionValue;
    select.append(option);
  }

  if (value !== undefined) select.value = value;

  label.append(select);
  $("#editor-fields").append(label);
  return select;
}

function openEditor(type, record = null) {
  const categories = type === "budget"
    ? state.categories.filter((category) => category.kind === "expense")
    : state.categories;

  if (type !== "category" && !record && !categories.length) {
    notify(
      type === "budget"
        ? "Create an expense category first."
        : "Create a category first.",
      true,
    );
    return;
  }

  editing = { type, record };
  $("#editor-form").reset();
  $("#editor-fields").replaceChildren();
  $("#editor-error").textContent = "";
  $("#editor-title").textContent =
    `${record ? "Edit" : "Add"} ${type}`;

  if (type === "category") {
    inputField("name", "Name", "text", record?.name, {
      required: "",
      maxlength: "50",
    });

    selectField("kind", "Type", [
      ["expense", "Expense"],
      ["income", "Income"],
    ], record?.kind);
  }

  if (type === "transaction") {
    selectField(
      "category_id",
      "Category",
      categories.map((category) => [
        category.id,
        `${category.name} · ${category.kind}`,
      ]),
      record?.category_id,
    );

    inputField("amount", "Amount ($)", "number", record?.amount, {
      required: "",
      min: "0.01",
      max: "99999999.99",
      step: "0.01",
    });

    inputField(
      "transaction_date",
      "Date",
      "date",
      record?.transaction_date || today(),
      { required: "" },
    );

    inputField("description", "Description (optional)", "text", record?.description, {
      maxlength: "255",
    });
  }

  if (type === "budget") {
    if (!record) {
      selectField(
        "category_id",
        "Expense category",
        categories.map((category) => [category.id, category.name]),
      );

      inputField("month", "Month", "month", $("#view-month").value, {
        required: "",
      });
    } else {
      $("#editor-fields").append(
        element("p", `${categoryName(record.category_id)} · ${record.month.slice(0, 7)}`, "muted"),
      );
    }

    inputField("monthly_limit", "Monthly limit ($)", "number", record?.monthly_limit, {
      required: "",
      min: "0.01",
      max: "99999999.99",
      step: "0.01",
    });
  }

  $("#editor").showModal();
}

document.querySelectorAll("[data-new]").forEach((button) => {
  button.addEventListener("click", () => openEditor(button.dataset.new));
});

$("#close-editor").addEventListener("click", () => $("#editor").close());

const paths = {
  category: "/categories",
  transaction: "/transactions",
  budget: "/budgets",
};

$("#editor-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const { type, record } = editing;
  const data = Object.fromEntries(new FormData(event.currentTarget));
  const button = event.currentTarget.querySelector("[type=submit]");
  let body;

  if (type === "category") {
    body = { name: data.name, kind: data.kind };
  } else if (type === "transaction") {
    body = {
      category_id: Number(data.category_id),
      amount: data.amount,
      transaction_date: data.transaction_date,
      description: data.description || null,
    };
  } else {
    body = { monthly_limit: data.monthly_limit };

    if (!record) {
      body.category_id = Number(data.category_id);
      body.month = `${data.month}-01`;
    }
  }

  button.disabled = true;
  $("#close-editor").disabled = true;
  $("#editor-error").textContent = "";

  let saved = false;

  try {
    const path = record
      ? `${paths[type]}/${record.id}`
      : paths[type];

    await api(path, {
      method: record ? "PATCH" : "POST",
      body,
    });

    saved = true;
    $("#editor").close();
    await loadData();
    notify(`${type[0].toUpperCase()}${type.slice(1)} saved.`);
  } catch (error) {
    if (saved) {
      notify(`Saved, but refreshing failed: ${error.message}`, true);
    } else if ($("#editor").open) {
      $("#editor-error").textContent = error.message;
    } else {
      notify(error.message, true);
    }
  } finally {
    button.disabled = false;
    $("#close-editor").disabled = false;
  }
});

async function removeRecord(type, record, button) {
  if (!window.confirm(`Delete this ${type}? This cannot be undone.`)) return;

  button.disabled = true;
  let deleted = false;

  try {
    await api(`${paths[type]}/${record.id}`, { method: "DELETE" });
    deleted = true;
    await loadData();
    notify(`${type[0].toUpperCase()}${type.slice(1)} deleted.`);
  } catch (error) {
    notify(
      deleted
        ? `Deleted, but refreshing failed: ${error.message}`
        : error.message,
      true,
    );
  } finally {
    button.disabled = false;
  }
}

if (state.token) {
  enterApp().catch((error) => {
    logout();
    notify(error.message, true);
  });
}