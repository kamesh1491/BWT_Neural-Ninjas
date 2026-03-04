/* ═══════════════════════════════════════════════════════════════════════
   ShieldAI — Dashboard JavaScript
   Fetches data from Flask API, renders charts, tables, and interactions.
   Now includes: system info, app usage, mood tracking, goals, recommendations.
   ═══════════════════════════════════════════════════════════════════════ */

const API = "";  // same origin

// ── State ───────────────────────────────────────────────────────────────
let dashboardData = {};
let chartInstances = {};
let currentLogPage = 1;
let selectedMoodScore = null;
let systemInfoData = null;

// ── Init ────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    setupNav();
    setupMoodEmojis();
    updateClock();
    setInterval(updateClock, 1000);
    loadSystemInfo();
    loadDashboard();
});

function updateClock() {
    const el = document.getElementById("header-time");
    if (el) el.textContent = new Date().toLocaleString("en-US", {
        weekday: "short", hour: "2-digit", minute: "2-digit", second: "2-digit"
    });
}


/* ═══════════════════════════════════════════════════════════════════════
   SYSTEM INFO
   ═══════════════════════════════════════════════════════════════════════ */
async function loadSystemInfo() {
    try {
        const res = await fetch(`${API}/api/system-info`);
        systemInfoData = await res.json();
        const s = systemInfoData;

        // Header
        document.getElementById("header-username").textContent = s.username;
        document.getElementById("header-machine").textContent = `${s.hostname} · ${s.os}`;
        const avatarEl = document.getElementById("header-avatar");
        if (avatarEl) avatarEl.querySelector("span").textContent = s.username.charAt(0).toUpperCase();

        // Welcome banner
        const hour = new Date().getHours();
        let greeting = "Good evening";
        if (hour < 12) greeting = "Good morning";
        else if (hour < 18) greeting = "Good afternoon";
        document.getElementById("welcome-greeting").textContent = `${greeting}, ${s.username}! 👋`;
        document.getElementById("welcome-sub").textContent = `${s.hostname} · ${s.os} · ${s.cpu_count} cores · ${s.ram_total_gb} GB RAM · Up ${s.uptime}`;

        // System stats in welcome
        document.getElementById("welcome-system-stats").innerHTML = `
            <div class="welcome-stat"><span class="welcome-stat-val">${s.cpu_percent}%</span><span class="welcome-stat-lbl">CPU</span></div>
            <div class="welcome-stat"><span class="welcome-stat-val">${s.ram_percent}%</span><span class="welcome-stat-lbl">RAM</span></div>
            <div class="welcome-stat"><span class="welcome-stat-val">${s.uptime}</span><span class="welcome-stat-lbl">Uptime</span></div>
        `;
    } catch (e) {
        console.error("System info load failed:", e);
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   NAVIGATION
   ═══════════════════════════════════════════════════════════════════════ */
function setupNav() {
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", e => {
            e.preventDefault();
            const page = item.dataset.page;
            if (page) switchPage(page);
        });
    });
}

function switchPage(page) {
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    const navEl = document.querySelector(`[data-page="${page}"]`);
    if (navEl) navEl.classList.add("active");

    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.classList.add("active");

    const titles = {
        dashboard: ["Security Dashboard", "Real-time insider threat monitoring and anomaly detection"],
        apps: ["App Usage", "Live system application monitoring and resource tracking"],
        mood: ["Mood Tracker", "Track your mood, energy, and stress to improve security decisions"],
        goals: ["My Goals", "Set and track personal productivity, security, and wellness goals"],
        alerts: ["Security Alerts", "Review and manage detected security anomalies"],
        users: ["Monitored Users", "User risk profiles and behavioral analysis"],
        logs: ["Activity Logs", "Detailed activity log stream with anomaly flags"],
    };
    const [h, sub] = titles[page] || ["Dashboard", ""];
    document.getElementById("page-heading").textContent = h;
    document.getElementById("page-subtitle").textContent = sub;

    if (page === "dashboard") loadDashboard();
    if (page === "apps") loadAppUsage();
    if (page === "mood") loadMoodPage();
    if (page === "goals") loadGoals();
    if (page === "alerts") loadAlerts();
    if (page === "users") loadUsers();
    if (page === "logs") loadLogs(1);

    document.getElementById("sidebar").classList.remove("open");
}

function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
}


/* ═══════════════════════════════════════════════════════════════════════
   DASHBOARD
   ═══════════════════════════════════════════════════════════════════════ */
async function loadDashboard() {
    try {
        const res = await fetch(`${API}/api/dashboard`);
        dashboardData = await res.json();
        renderStats(dashboardData);
        renderHourlyChart(dashboardData.hourly_activity);
        renderRiskChart(dashboardData.risk_distribution);
        renderTypesChart(dashboardData.activity_types);
        renderTrendChart(dashboardData.alert_trend);
        loadTopRiskUsers();
        document.getElementById("alert-badge").textContent = dashboardData.active_alerts || 0;
        loadRecommendations();
    } catch (e) {
        console.error("Dashboard load failed:", e);
    }
}

function renderStats(d) {
    animateValue("stat-total-users", d.total_users);
    animateValue("stat-active-alerts", d.active_alerts);
    animateValue("stat-avg-risk", d.avg_risk_score);
    animateValue("stat-anomalies", d.anomaly_logs);
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const duration = 800;
    const startTime = performance.now();
    const isFloat = !Number.isInteger(target);
    function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        const current = target * ease;
        el.textContent = isFloat ? current.toFixed(1) : Math.round(current);
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}


/* ── Recommendations ─────────────────────────────────────────────────── */
async function loadRecommendations() {
    try {
        const res = await fetch(`${API}/api/recommendations`);
        const recs = await res.json();
        const grid = document.getElementById("recs-grid");
        if (!recs.length) {
            grid.innerHTML = '<div class="rec-card"><span class="rec-icon">✨</span><div><strong>All Clear</strong><p>Everything looks good!</p></div></div>';
            return;
        }
        grid.innerHTML = recs.map(r => `
            <div class="rec-card rec-${r.priority}">
                <span class="rec-icon">${r.icon}</span>
                <div class="rec-body">
                    <div class="rec-top">
                        <strong>${escHtml(r.title)}</strong>
                        <span class="rec-cat">${escHtml(r.category)}</span>
                    </div>
                    <p>${escHtml(r.text)}</p>
                </div>
            </div>
        `).join("");
    } catch (e) {
        console.error("Recommendations load failed:", e);
    }
}


/* ── Charts ──────────────────────────────────────────────────────────── */
const chartColors = {
    blue: "rgba(59,130,246,0.8)",
    purple: "rgba(139,92,246,0.8)",
    cyan: "rgba(6,182,212,0.8)",
    pink: "rgba(236,72,153,0.8)",
    orange: "rgba(249,115,22,0.8)",
    green: "rgba(16,185,129,0.8)",
    red: "rgba(239,68,68,0.8)",
    yellow: "rgba(234,179,8,0.8)",
};

const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: "rgba(17,24,39,0.95)",
            titleColor: "#f1f5f9", bodyColor: "#94a3b8",
            borderColor: "rgba(255,255,255,0.08)", borderWidth: 1,
            padding: 12, cornerRadius: 8,
            bodyFont: { family: "Inter" }, titleFont: { family: "Inter", weight: 600 },
        },
    },
    scales: {
        x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#64748b", font: { family: "Inter", size: 11 } } },
        y: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#64748b", font: { family: "Inter", size: 11 } } },
    },
};

function destroyChart(key) {
    if (chartInstances[key]) { chartInstances[key].destroy(); chartInstances[key] = null; }
}

function renderHourlyChart(data) {
    destroyChart("hourly");
    const labels = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, "0")}:00`);
    const values = labels.map((_, i) => data[String(i).padStart(2, "0")] || 0);
    const ctx = document.getElementById("chart-hourly").getContext("2d");
    chartInstances.hourly = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{ data: values, backgroundColor: values.map((_, i) => (i < 7 || i > 20) ? chartColors.red : chartColors.blue), borderRadius: 4, borderSkipped: false }],
        },
        options: { ...defaultChartOptions, plugins: { ...defaultChartOptions.plugins, tooltip: { ...defaultChartOptions.plugins.tooltip, callbacks: { title: ctx => ctx[0].label, label: ctx => `${ctx.raw} activities` } } } },
    });
}

function renderRiskChart(dist) {
    destroyChart("risk");
    const ctx = document.getElementById("chart-risk").getContext("2d");
    chartInstances.risk = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Critical", "High", "Medium", "Low"],
            datasets: [{ data: [dist.Critical, dist.High, dist.Medium, dist.Low], backgroundColor: [chartColors.red, chartColors.orange, chartColors.yellow, chartColors.green], borderColor: "rgba(10,14,26,0.8)", borderWidth: 3, hoverOffset: 8 }],
        },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: "68%",
            plugins: { legend: { position: "right", labels: { color: "#94a3b8", font: { family: "Inter", size: 12 }, padding: 16, usePointStyle: true, pointStyleWidth: 10 } }, tooltip: defaultChartOptions.plugins.tooltip },
        },
    });
}

function renderTypesChart(types) {
    destroyChart("types");
    const labels = Object.keys(types);
    const values = Object.values(types);
    const colors = [chartColors.blue, chartColors.purple, chartColors.cyan, chartColors.orange, chartColors.red];
    const ctx = document.getElementById("chart-types").getContext("2d");
    chartInstances.types = new Chart(ctx, {
        type: "bar",
        data: { labels: labels.map(l => l.replace(/_/g, " ")), datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length), borderRadius: 6, borderSkipped: false }] },
        options: { ...defaultChartOptions, indexAxis: "y" },
    });
}

function renderTrendChart(trend) {
    destroyChart("trend");
    if (!trend || !trend.length) return;
    const labels = trend.map(t => { const d = new Date(t.date); return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }); });
    const values = trend.map(t => t.count);
    const ctx = document.getElementById("chart-trend").getContext("2d");
    const grad = ctx.createLinearGradient(0, 0, 0, 240);
    grad.addColorStop(0, "rgba(236,72,153,0.3)"); grad.addColorStop(1, "rgba(236,72,153,0.01)");
    chartInstances.trend = new Chart(ctx, {
        type: "line",
        data: { labels, datasets: [{ data: values, borderColor: chartColors.pink, backgroundColor: grad, fill: true, tension: 0.4, pointRadius: 3, pointBackgroundColor: chartColors.pink, pointBorderColor: "#0a0e1a", pointBorderWidth: 2 }] },
        options: defaultChartOptions,
    });
}


/* ── Top Risk Users (Dashboard) ──────────────────────────────────────── */
async function loadTopRiskUsers() {
    try {
        const res = await fetch(`${API}/api/users`);
        const users = await res.json();
        const top = users.slice(0, 8);
        const tbody = document.getElementById("top-risk-tbody");
        tbody.innerHTML = top.map(u => `
            <tr>
                <td><strong>${escHtml(u.full_name)}</strong><br><span style="font-size:0.75rem;color:var(--text-muted)">@${escHtml(u.username)}</span></td>
                <td>${escHtml(u.department)}</td>
                <td><strong>${u.risk_score}</strong></td>
                <td>${riskBadge(u.risk_level)}</td>
                <td><button class="btn-view" onclick="openUserModal(${u.id})">View</button></td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Top risk users load failed:", e);
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   APP USAGE PAGE
   ═══════════════════════════════════════════════════════════════════════ */
async function loadAppUsage() {
    try {
        const [appsRes, sysRes] = await Promise.all([
            fetch(`${API}/api/app-usage`),
            systemInfoData ? Promise.resolve(null) : fetch(`${API}/api/system-info`),
        ]);
        const appsData = await appsRes.json();
        if (sysRes) systemInfoData = await sysRes.json();

        document.getElementById("apps-count").textContent = `${appsData.total_processes} processes`;

        // System info card
        const s = systemInfoData;
        document.getElementById("system-info-body").innerHTML = `
            <div class="sysinfo-grid">
                <div class="sysinfo-item"><span class="sysinfo-label">OS</span><span class="sysinfo-value">${s.os}</span></div>
                <div class="sysinfo-item"><span class="sysinfo-label">Machine</span><span class="sysinfo-value">${s.machine}</span></div>
                <div class="sysinfo-item"><span class="sysinfo-label">CPU</span><span class="sysinfo-value">${s.cpu_count} cores · ${s.cpu_percent}%</span></div>
                <div class="sysinfo-item"><span class="sysinfo-label">RAM</span><span class="sysinfo-value">${s.ram_used_gb}/${s.ram_total_gb} GB (${s.ram_percent}%)</span></div>
                <div class="sysinfo-item"><span class="sysinfo-label">Processor</span><span class="sysinfo-value">${s.processor}</span></div>
                <div class="sysinfo-item"><span class="sysinfo-label">Uptime</span><span class="sysinfo-value">${s.uptime}</span></div>
            </div>
            <div class="ram-bar-container">
                <div class="ram-bar" style="width:${s.ram_percent}%"></div>
            </div>
            <div class="ram-bar-label">${s.ram_percent}% RAM Used</div>
        `;

        // Category chart
        renderAppCategoryChart(appsData.categories);

        // Apps table
        const catColors = { "Browser": "blue", "Dev Tool": "green", "Communication": "cyan", "Productivity": "purple", "Media": "pink", "Security": "orange", "System": "muted" };
        const tbody = document.getElementById("apps-tbody");
        tbody.innerHTML = appsData.apps.map(a => `
            <tr>
                <td><strong>${escHtml(a.name)}</strong></td>
                <td><span class="cat-badge cat-${catColors[a.category] || 'muted'}">${escHtml(a.category)}</span></td>
                <td>${a.instances}</td>
                <td>
                    <div class="usage-bar-wrap">
                        <div class="usage-bar usage-cpu" style="width:${Math.min(a.cpu_percent, 100)}%"></div>
                        <span>${a.cpu_percent}%</span>
                    </div>
                </td>
                <td>
                    <div class="usage-bar-wrap">
                        <div class="usage-bar usage-mem" style="width:${Math.min(a.memory_percent, 100)}%"></div>
                        <span>${a.memory_percent}%</span>
                    </div>
                </td>
                <td style="color:var(--text-muted)">${a.started}</td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("App usage load failed:", e);
    }
}

function renderAppCategoryChart(categories) {
    destroyChart("appCategories");
    const labels = Object.keys(categories);
    const values = Object.values(categories);
    const colors = [chartColors.blue, chartColors.green, chartColors.cyan, chartColors.purple, chartColors.pink, chartColors.orange, chartColors.yellow, chartColors.red];
    const ctx = document.getElementById("chart-app-categories").getContext("2d");
    chartInstances.appCategories = new Chart(ctx, {
        type: "doughnut",
        data: { labels, datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length), borderColor: "rgba(10,14,26,0.8)", borderWidth: 3, hoverOffset: 8 }] },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: "65%",
            plugins: { legend: { position: "right", labels: { color: "#94a3b8", font: { family: "Inter", size: 11 }, padding: 12, usePointStyle: true, pointStyleWidth: 10 } }, tooltip: defaultChartOptions.plugins.tooltip },
        },
    });
}


/* ═══════════════════════════════════════════════════════════════════════
   MOOD TRACKER PAGE
   ═══════════════════════════════════════════════════════════════════════ */
function setupMoodEmojis() {
    document.querySelectorAll(".mood-emoji").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".mood-emoji").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            selectedMoodScore = parseInt(btn.dataset.score);
        });
    });
}

async function submitMood() {
    if (!selectedMoodScore) {
        showToast("Please select a mood first!");
        return;
    }
    const btn = document.getElementById("btn-submit-mood");
    btn.disabled = true; btn.textContent = "Submitting...";
    try {
        await fetch(`${API}/api/mood`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mood_score: selectedMoodScore,
                energy_level: parseInt(document.getElementById("energy-slider").value),
                stress_level: parseInt(document.getElementById("stress-slider").value),
                notes: document.getElementById("mood-notes").value,
            }),
        });
        showToast("Mood check-in recorded! ✅");
        selectedMoodScore = null;
        document.querySelectorAll(".mood-emoji").forEach(b => b.classList.remove("selected"));
        document.getElementById("mood-notes").value = "";
        loadMoodPage();
    } catch (e) {
        showToast("Failed to submit mood.");
    } finally {
        btn.disabled = false; btn.textContent = "Submit Check-in";
    }
}

async function loadMoodPage() {
    try {
        const [moodRes, insightRes] = await Promise.all([
            fetch(`${API}/api/mood`),
            fetch(`${API}/api/mood-insights`),
        ]);
        const moodEntries = await moodRes.json();
        const insights = await insightRes.json();

        // Averages
        document.getElementById("mood-averages").innerHTML = `
            <div class="mood-avg"><span class="mood-avg-val">${insights.avg_mood || "—"}</span><span class="mood-avg-lbl">Avg Mood</span></div>
            <div class="mood-avg"><span class="mood-avg-val">${insights.avg_energy || "—"}</span><span class="mood-avg-lbl">Avg Energy</span></div>
            <div class="mood-avg"><span class="mood-avg-val">${insights.avg_stress || "—"}</span><span class="mood-avg-lbl">Avg Stress</span></div>
            <div class="mood-avg"><span class="mood-avg-val">${insights.total_entries || 0}</span><span class="mood-avg-lbl">Check-ins</span></div>
        `;

        // Insights
        const list = document.getElementById("mood-insights-list");
        if (insights.insights && insights.insights.length) {
            list.innerHTML = insights.insights.map(i => `
                <div class="insight-item insight-${i.type}">
                    <span class="insight-icon">${i.icon}</span>
                    <div><strong>${escHtml(i.title)}</strong><p>${escHtml(i.text)}</p></div>
                </div>
            `).join("");
        } else {
            list.innerHTML = '<p style="color:var(--text-muted)">No insights yet. Submit more check-ins!</p>';
        }

        // Mood history chart
        renderMoodChart(moodEntries.reverse());
    } catch (e) {
        console.error("Mood page load failed:", e);
    }
}

function renderMoodChart(entries) {
    destroyChart("moodHistory");
    if (!entries.length) return;
    const labels = entries.map(e => {
        const d = new Date(e.timestamp);
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    });

    const ctx = document.getElementById("chart-mood-history").getContext("2d");
    const gradMood = ctx.createLinearGradient(0, 0, 0, 280);
    gradMood.addColorStop(0, "rgba(59,130,246,0.3)"); gradMood.addColorStop(1, "rgba(59,130,246,0.01)");
    const gradStress = ctx.createLinearGradient(0, 0, 0, 280);
    gradStress.addColorStop(0, "rgba(239,68,68,0.2)"); gradStress.addColorStop(1, "rgba(239,68,68,0.01)");

    chartInstances.moodHistory = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                { label: "Mood", data: entries.map(e => e.mood_score), borderColor: chartColors.blue, backgroundColor: gradMood, fill: true, tension: 0.4, pointRadius: 4, pointBackgroundColor: chartColors.blue, pointBorderColor: "#0a0e1a", pointBorderWidth: 2 },
                { label: "Energy", data: entries.map(e => e.energy_level), borderColor: chartColors.green, fill: false, tension: 0.4, pointRadius: 3, borderDash: [5, 5] },
                { label: "Stress", data: entries.map(e => e.stress_level), borderColor: chartColors.red, backgroundColor: gradStress, fill: true, tension: 0.4, pointRadius: 3 },
            ],
        },
        options: {
            ...defaultChartOptions,
            scales: {
                ...defaultChartOptions.scales,
                y: { ...defaultChartOptions.scales.y, min: 0, max: 6, ticks: { ...defaultChartOptions.scales.y.ticks, stepSize: 1 } },
            },
            plugins: {
                ...defaultChartOptions.plugins,
                legend: { display: true, labels: { color: "#94a3b8", font: { family: "Inter", size: 11 }, usePointStyle: true, padding: 20 } },
            },
        },
    });
}


/* ═══════════════════════════════════════════════════════════════════════
   GOALS PAGE
   ═══════════════════════════════════════════════════════════════════════ */
async function loadGoals() {
    try {
        const res = await fetch(`${API}/api/goals`);
        const goals = await res.json();
        const grid = document.getElementById("goals-grid");
        if (!goals.length) {
            grid.innerHTML = '<p style="color:var(--text-muted);padding:20px;text-align:center">No goals yet. Create one above! 🎯</p>';
            return;
        }

        const catIcons = { security: "🛡️", productivity: "📋", wellness: "🧘", project: "💻", learning: "📚", communication: "💬" };
        grid.innerHTML = goals.map(g => {
            const progress = g.progress;
            const isOverdue = g.deadline && new Date(g.deadline) < new Date() && !g.is_completed;
            const barColor = g.is_completed ? "var(--accent-green)" : isOverdue ? "var(--accent-red)" : progress > 60 ? "var(--accent-blue)" : "var(--accent-orange)";
            const deadlineText = g.deadline ? new Date(g.deadline).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "No deadline";
            return `
                <div class="goal-card ${g.is_completed ? 'goal-completed' : ''} ${isOverdue ? 'goal-overdue' : ''}">
                    <div class="goal-card-header">
                        <span class="goal-cat-icon">${catIcons[g.category] || "📌"}</span>
                        <span class="goal-cat-label">${g.category}</span>
                        ${g.is_completed ? '<span class="badge badge-low">Done</span>' : isOverdue ? '<span class="badge badge-critical">Overdue</span>' : ''}
                        <button class="goal-delete" onclick="deleteGoal(${g.id})" title="Delete">×</button>
                    </div>
                    <h4 class="goal-title">${escHtml(g.title)}</h4>
                    <div class="goal-progress-bar">
                        <div class="goal-progress-fill" style="width:${progress}%;background:${barColor}"></div>
                    </div>
                    <div class="goal-meta">
                        <span>${g.current_value} / ${g.target_value} ${g.unit}</span>
                        <span>${progress}%</span>
                    </div>
                    <div class="goal-deadline">📅 ${deadlineText}</div>
                    ${!g.is_completed ? `
                        <div class="goal-actions">
                            <input type="number" class="goal-update-input" id="goal-val-${g.id}" placeholder="New value" step="1" value="${g.current_value}">
                            <button class="btn-view" onclick="updateGoal(${g.id})">Update</button>
                            <button class="btn-complete" onclick="completeGoal(${g.id})">✓ Complete</button>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join("");
    } catch (e) {
        console.error("Goals load failed:", e);
    }
}

async function createGoal() {
    const title = document.getElementById("goal-title").value.trim();
    if (!title) { showToast("Please enter a goal title!"); return; }
    try {
        await fetch(`${API}/api/goals`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title,
                category: document.getElementById("goal-category").value,
                target_value: parseFloat(document.getElementById("goal-target").value) || 100,
                unit: document.getElementById("goal-unit").value || "%",
                deadline: document.getElementById("goal-deadline").value || null,
            }),
        });
        document.getElementById("goal-title").value = "";
        showToast("Goal created! 🎯");
        loadGoals();
    } catch (e) {
        showToast("Failed to create goal.");
    }
}

async function updateGoal(id) {
    const val = parseFloat(document.getElementById(`goal-val-${id}`).value);
    try {
        await fetch(`${API}/api/goals/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ current_value: val }),
        });
        showToast("Goal updated! 📈");
        loadGoals();
    } catch (e) {
        showToast("Failed to update goal.");
    }
}

async function completeGoal(id) {
    try {
        await fetch(`${API}/api/goals/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_completed: true }),
        });
        showToast("Goal completed! 🎉");
        loadGoals();
    } catch (e) {
        showToast("Failed to complete goal.");
    }
}

async function deleteGoal(id) {
    try {
        await fetch(`${API}/api/goals/${id}`, { method: "DELETE" });
        showToast("Goal deleted.");
        loadGoals();
    } catch (e) {
        showToast("Failed to delete goal.");
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   ALERTS PAGE
   ═══════════════════════════════════════════════════════════════════════ */
async function loadAlerts() {
    try {
        const res = await fetch(`${API}/api/alerts`);
        const alerts = await res.json();
        document.getElementById("alerts-count").textContent = `${alerts.length} alerts`;
        const tbody = document.getElementById("alerts-tbody");
        tbody.innerHTML = alerts.map(a => `
            <tr>
                <td>${severityBadge(a.severity)}</td>
                <td><strong>${escHtml(a.full_name || "")}</strong></td>
                <td><span class="activity-type type-${a.category}">${escHtml(a.category.replace(/_/g, " "))}</span></td>
                <td>${escHtml(a.title)}</td>
                <td style="white-space:nowrap;color:var(--text-muted)">${formatTime(a.timestamp)}</td>
                <td>${a.is_resolved ? '<span class="badge badge-resolved">Resolved</span>' : '<span class="badge badge-critical">Open</span>'}</td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Alerts load failed:", e);
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   USERS PAGE
   ═══════════════════════════════════════════════════════════════════════ */
async function loadUsers() {
    try {
        const res = await fetch(`${API}/api/users`);
        const users = await res.json();
        const tbody = document.getElementById("users-tbody");
        tbody.innerHTML = users.map(u => `
            <tr>
                <td><strong>${escHtml(u.full_name)}</strong><br><span style="font-size:0.75rem;color:var(--text-muted)">@${escHtml(u.username)}</span></td>
                <td style="color:var(--text-muted)">${escHtml(u.email)}</td>
                <td>${escHtml(u.department)}</td>
                <td>${escHtml(u.role)}</td>
                <td><strong>${u.risk_score}</strong></td>
                <td>${riskBadge(u.risk_level)}</td>
                <td><button class="btn-view" onclick="openUserModal(${u.id})">View</button></td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Users load failed:", e);
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   LOGS PAGE
   ═══════════════════════════════════════════════════════════════════════ */
async function loadLogs(page) {
    currentLogPage = page;
    try {
        const res = await fetch(`${API}/api/logs?page=${page}&per_page=50`);
        const data = await res.json();
        document.getElementById("logs-count").textContent = `${data.total} total logs — page ${data.page}`;
        const tbody = document.getElementById("logs-tbody");
        tbody.innerHTML = data.logs.map(l => `
            <tr>
                <td style="white-space:nowrap;color:var(--text-muted);font-variant-numeric:tabular-nums">${formatTime(l.timestamp)}</td>
                <td><strong>${escHtml(l.username || "")}</strong></td>
                <td><span class="activity-type type-${l.activity_type}">${escHtml(l.activity_type.replace(/_/g, " "))}</span></td>
                <td>${escHtml(l.description || "")}</td>
                <td style="color:var(--text-muted)">${escHtml(l.device || "")}</td>
                <td style="color:var(--text-muted)">${escHtml(l.location || "")}</td>
                <td><span class="anomaly-dot ${l.is_anomaly ? "yes" : "no"}"></span></td>
            </tr>
        `).join("");

        const totalPages = Math.ceil(data.total / data.per_page);
        const pagDiv = document.getElementById("logs-pagination");
        let pagHtml = `<button ${page <= 1 ? "disabled" : ""} onclick="loadLogs(${page - 1})">← Prev</button>`;
        const start = Math.max(1, page - 2);
        const end = Math.min(totalPages, page + 2);
        for (let i = start; i <= end; i++) {
            pagHtml += `<button class="${i === page ? "active" : ""}" onclick="loadLogs(${i})">${i}</button>`;
        }
        pagHtml += `<button ${page >= totalPages ? "disabled" : ""} onclick="loadLogs(${page + 1})">Next →</button>`;
        pagDiv.innerHTML = pagHtml;
    } catch (e) {
        console.error("Logs load failed:", e);
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   USER DETAIL MODAL
   ═══════════════════════════════════════════════════════════════════════ */
async function openUserModal(userId) {
    try {
        const res = await fetch(`${API}/api/users/${userId}/activity`);
        const data = await res.json();
        const u = data.user;
        const acts = data.activities;

        document.getElementById("modal-user-name").textContent = u.full_name;
        document.getElementById("modal-user-info").innerHTML = `
            <div class="info-item"><span class="info-label">Username</span><span class="info-value">@${escHtml(u.username)}</span></div>
            <div class="info-item"><span class="info-label">Email</span><span class="info-value">${escHtml(u.email)}</span></div>
            <div class="info-item"><span class="info-label">Department</span><span class="info-value">${escHtml(u.department)}</span></div>
            <div class="info-item"><span class="info-label">Role</span><span class="info-value">${escHtml(u.role)}</span></div>
            <div class="info-item"><span class="info-label">Risk Score</span><span class="info-value" style="font-size:1.2rem">${u.risk_score}</span></div>
            <div class="info-item"><span class="info-label">Risk Level</span><span class="info-value">${riskBadge(u.risk_level)}</span></div>
        `;
        document.getElementById("modal-activity-list").innerHTML = `
            <h4>Recent Activity (${acts.length})</h4>
            ${acts.slice(0, 50).map(a => `
                <div class="activity-item">
                    <span class="activity-time">${formatTime(a.timestamp)}</span>
                    <span class="activity-type type-${a.activity_type}">${a.activity_type.replace(/_/g, " ")}</span>
                    <span class="activity-desc">${escHtml(a.description || "")}</span>
                    <span class="activity-anomaly">${a.is_anomaly ? '<span class="anomaly-dot yes"></span>' : ''}</span>
                </div>
            `).join("")}
        `;
        document.getElementById("user-modal").classList.add("visible");
    } catch (e) {
        console.error("User modal load failed:", e);
    }
}

function closeModal() {
    document.getElementById("user-modal").classList.remove("visible");
}

document.addEventListener("click", e => {
    if (e.target.id === "user-modal") closeModal();
});


/* ═══════════════════════════════════════════════════════════════════════
   ML ANALYSIS TRIGGER
   ═══════════════════════════════════════════════════════════════════════ */
async function triggerAnalysis() {
    const btn = document.getElementById("btn-analyze");
    btn.disabled = true;
    btn.innerHTML = '<svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg> Analyzing…';
    try {
        const res = await fetch(`${API}/api/analyze`, { method: "POST" });
        const data = await res.json();
        showToast(`Analysis complete — ${data.anomalies || 0} anomalies detected in ${data.total_users || 0} users`);
        loadDashboard();
    } catch (e) {
        showToast("Analysis failed. Check server logs.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg> Run ML Analysis';
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   HELPERS
   ═══════════════════════════════════════════════════════════════════════ */
function escHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

function formatTime(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function riskBadge(level) {
    const cls = { Critical: "badge-critical", High: "badge-high", Medium: "badge-medium", Low: "badge-low" }[level] || "badge-low";
    return `<span class="badge ${cls}">${level}</span>`;
}

function severityBadge(sev) { return riskBadge(sev); }

function showToast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.classList.add("visible");
    setTimeout(() => el.classList.remove("visible"), 4000);
}
