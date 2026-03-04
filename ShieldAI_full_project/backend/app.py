"""
Flask Application — Insider Threat Detection System
Serves the REST API and the frontend dashboard.
Includes: system info, app usage monitoring, mood tracking, goals, and smart recommendations.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from models import init_db, get_session, User, ActivityLog, Alert, MoodEntry, UserGoal
from ml_engine import run_analysis
from seed_data import seed
from datetime import datetime, timedelta
import os, platform, socket, psutil

app = Flask(__name__, static_folder="../static", static_url_path="")
CORS(app)

# ── Frontend ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ══════════════════════════════════════════════════════════════════════════
#  SYSTEM INFO & APP USAGE
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/system-info")
def system_info():
    """Return real system information about the current machine and user."""
    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get("USERNAME", os.environ.get("USER", "Unknown"))

    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes = remainder // 60

    mem = psutil.virtual_memory()

    return jsonify({
        "username": username,
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "N/A",
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_total_gb": round(mem.total / (1024**3), 1),
        "ram_used_gb": round(mem.used / (1024**3), 1),
        "ram_percent": mem.percent,
        "uptime": f"{hours}h {minutes}m",
        "boot_time": boot_time.isoformat(),
        "current_time": datetime.now().isoformat(),
    })


# ── App category mapping ──────────────────────────────────────────────────
APP_CATEGORIES = {
    "chrome": "Browser", "firefox": "Browser", "msedge": "Browser",
    "opera": "Browser", "brave": "Browser", "vivaldi": "Browser",
    "code": "Dev Tool", "pycharm": "Dev Tool", "idea": "Dev Tool",
    "devenv": "Dev Tool", "node": "Dev Tool", "python": "Dev Tool",
    "java": "Dev Tool", "docker": "Dev Tool", "git": "Dev Tool",
    "powershell": "Dev Tool", "cmd": "Dev Tool", "wt": "Dev Tool",
    "windowsterminal": "Dev Tool",
    "teams": "Communication", "slack": "Communication", "discord": "Communication",
    "zoom": "Communication", "outlook": "Communication", "skype": "Communication",
    "whatsapp": "Communication", "telegram": "Communication",
    "winword": "Productivity", "excel": "Productivity", "powerpnt": "Productivity",
    "onenote": "Productivity", "notion": "Productivity", "notepad": "Productivity",
    "obsidian": "Productivity",
    "spotify": "Media", "vlc": "Media", "wmplayer": "Media",
    "malwarebytes": "Security", "msmpeng": "Security",
}

# Maps goal categories to the app categories that should be used
GOAL_APP_MAP = {
    "productivity": ["Dev Tool", "Productivity"],
    "security":     ["Dev Tool", "Security"],
    "wellness":     [],  # no specific apps
    "project":      ["Dev Tool"],
    "learning":     ["Browser", "Dev Tool", "Productivity"],
    "communication":["Communication"],
}


def _categorize_app(name):
    name_lower = name.lower().replace(".exe", "")
    for key, cat in APP_CATEGORIES.items():
        if key in name_lower:
            return cat
    return "System"


def _get_running_app_summary():
    """Get a summary of running app categories and their resource usage."""
    categories = {}
    for proc in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            name = info["name"] or ""
            cat = _categorize_app(name)
            if cat not in categories:
                categories[cat] = {"count": 0, "cpu": 0, "mem": 0, "apps": set()}
            categories[cat]["count"] += 1
            categories[cat]["cpu"] += info.get("cpu_percent", 0) or 0
            categories[cat]["mem"] += info.get("memory_percent", 0) or 0
            categories[cat]["apps"].add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # Convert sets to lists for JSON
    for cat in categories:
        categories[cat]["apps"] = list(categories[cat]["apps"])[:10]
        categories[cat]["cpu"] = round(categories[cat]["cpu"], 1)
        categories[cat]["mem"] = round(categories[cat]["mem"], 1)
    return categories


@app.route("/api/app-usage")
def app_usage():
    """Return a snapshot of running applications with resource usage."""
    seen = {}
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "create_time"]):
        try:
            info = proc.info
            name = info["name"] or "Unknown"
            if name not in seen:
                seen[name] = {
                    "name": name,
                    "category": _categorize_app(name),
                    "pids": [],
                    "cpu_percent": 0.0,
                    "memory_percent": 0.0,
                    "started": info.get("create_time"),
                }
            seen[name]["pids"].append(info["pid"])
            seen[name]["cpu_percent"] += info.get("cpu_percent", 0) or 0
            seen[name]["memory_percent"] += info.get("memory_percent", 0) or 0
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    apps = sorted(seen.values(), key=lambda x: x["memory_percent"], reverse=True)

    categories = {}
    for a in apps:
        cat = a["category"]
        categories[cat] = categories.get(cat, 0) + 1

    top_apps = []
    for a in apps[:50]:
        top_apps.append({
            "name": a["name"],
            "category": a["category"],
            "instances": len(a["pids"]),
            "cpu_percent": round(a["cpu_percent"], 1),
            "memory_percent": round(a["memory_percent"], 1),
            "started": datetime.fromtimestamp(a["started"]).strftime("%H:%M") if a.get("started") else "—",
        })

    return jsonify({
        "total_processes": len(apps),
        "categories": categories,
        "apps": top_apps,
    })


# ══════════════════════════════════════════════════════════════════════════
#  MOOD TRACKING
# ══════════════════════════════════════════════════════════════════════════

MOOD_LABELS = {1: "Stressed", 2: "Anxious", 3: "Neutral", 4: "Calm", 5: "Energized"}

@app.route("/api/mood", methods=["POST"])
def submit_mood():
    data = request.json or {}
    score = data.get("mood_score", 3)
    entry = MoodEntry(
        mood_score=score,
        mood_label=MOOD_LABELS.get(score, "Neutral"),
        energy_level=data.get("energy_level", 3),
        stress_level=data.get("stress_level", 3),
        notes=data.get("notes", ""),
        timestamp=datetime.utcnow(),
    )
    session = get_session()
    try:
        session.add(entry)
        session.commit()
        return jsonify({"status": "ok", "entry": entry.to_dict()})
    finally:
        session.close()


@app.route("/api/mood")
def get_mood():
    session = get_session()
    try:
        entries = (
            session.query(MoodEntry)
            .order_by(MoodEntry.timestamp.desc())
            .limit(90)
            .all()
        )
        return jsonify([e.to_dict() for e in entries])
    finally:
        session.close()


@app.route("/api/mood-insights")
def mood_insights():
    """Correlate mood with threat data to produce actionable insights."""
    session = get_session()
    try:
        entries = session.query(MoodEntry).order_by(MoodEntry.timestamp.desc()).limit(30).all()
        if not entries:
            return jsonify({"insights": [], "avg_mood": 0, "avg_stress": 0, "avg_energy": 0})

        avg_mood = sum(e.mood_score for e in entries) / len(entries)
        avg_stress = sum(e.stress_level for e in entries) / len(entries)
        avg_energy = sum(e.energy_level for e in entries) / len(entries)

        total_alerts = session.query(Alert).filter_by(is_resolved=False).count()
        anomaly_count = session.query(ActivityLog).filter_by(is_anomaly=True).count()

        insights = []
        if avg_stress >= 4:
            insights.append({
                "type": "warning", "icon": "⚠️", "title": "High Stress Alert",
                "text": f"Your average stress is {avg_stress:.1f}/5. High stress correlates with reduced security awareness. Take breaks.",
            })
        if avg_mood <= 2:
            insights.append({
                "type": "danger", "icon": "🔴", "title": "Low Mood Detected",
                "text": "Persistent low mood can impact decision-making. Consider stepping away from high-risk tasks.",
            })
        if avg_energy <= 2:
            insights.append({
                "type": "info", "icon": "🔋", "title": "Low Energy Pattern",
                "text": f"Energy averaging {avg_energy:.1f}/5. Schedule critical reviews for high-energy hours.",
            })
        if avg_mood >= 4 and avg_stress <= 2:
            insights.append({
                "type": "success", "icon": "✅", "title": "Optimal State",
                "text": "You're in a great mental state! Ideal time for thorough security reviews and complex threat analysis.",
            })
        if total_alerts > 5:
            insights.append({
                "type": "warning", "icon": "🛡️", "title": "Active Threat Load",
                "text": f"{total_alerts} unresolved alerts. Prioritize review during calm, high-energy periods.",
            })
        if not insights:
            insights.append({
                "type": "info", "icon": "📊", "title": "Baseline Normal",
                "text": "Your mood and stress levels are within normal range. Keep monitoring for patterns.",
            })

        return jsonify({
            "insights": insights,
            "avg_mood": round(avg_mood, 1),
            "avg_stress": round(avg_stress, 1),
            "avg_energy": round(avg_energy, 1),
            "total_entries": len(entries),
            "active_alerts": total_alerts,
            "anomaly_count": anomaly_count,
        })
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════════════════
#  GOALS
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/goals")
def get_goals():
    session = get_session()
    try:
        goals = session.query(UserGoal).order_by(UserGoal.created_at.desc()).all()
        return jsonify([g.to_dict() for g in goals])
    finally:
        session.close()


@app.route("/api/goals", methods=["POST"])
def create_goal():
    data = request.json or {}
    deadline = None
    if data.get("deadline"):
        try:
            deadline = datetime.fromisoformat(data["deadline"])
        except Exception:
            deadline = datetime.utcnow() + timedelta(days=30)

    goal = UserGoal(
        title=data.get("title", "New Goal"),
        category=data.get("category", "productivity"),
        target_value=data.get("target_value", 100),
        current_value=data.get("current_value", 0),
        unit=data.get("unit", "%"),
        deadline=deadline,
    )
    session = get_session()
    try:
        session.add(goal)
        session.commit()
        return jsonify({"status": "ok", "goal": goal.to_dict()})
    finally:
        session.close()


@app.route("/api/goals/<int:goal_id>", methods=["PUT"])
def update_goal(goal_id):
    session = get_session()
    try:
        goal = session.query(UserGoal).get(goal_id)
        if not goal:
            return jsonify({"error": "Goal not found"}), 404
        data = request.json or {}
        if "current_value" in data:
            goal.current_value = data["current_value"]
        if "is_completed" in data:
            goal.is_completed = data["is_completed"]
        if "title" in data:
            goal.title = data["title"]
        if goal.current_value >= goal.target_value:
            goal.is_completed = True
        session.commit()
        return jsonify({"status": "ok", "goal": goal.to_dict()})
    finally:
        session.close()


@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    session = get_session()
    try:
        goal = session.query(UserGoal).get(goal_id)
        if not goal:
            return jsonify({"error": "Goal not found"}), 404
        session.delete(goal)
        session.commit()
        return jsonify({"status": "deleted"})
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════════════════
#  RECOMMENDATIONS ENGINE — correlates mood, app usage, goals, threats
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/recommendations")
def get_recommendations():
    """Smart recommendations based on mood, LIVE app usage, goals, and threat data."""
    session = get_session()
    try:
        recent_mood = session.query(MoodEntry).order_by(MoodEntry.timestamp.desc()).first()
        active_alerts = session.query(Alert).filter_by(is_resolved=False).count()
        goals = session.query(UserGoal).filter_by(is_completed=False).all()

        mood_score = recent_mood.mood_score if recent_mood else 3
        stress = recent_mood.stress_level if recent_mood else 3
        energy = recent_mood.energy_level if recent_mood else 3

        # Get live app usage breakdown
        running_cats = _get_running_app_summary()

        recs = []

        # ── Screen-time vs Goals correlation ──
        for goal in goals:
            goal_cat = goal.category.lower()
            relevant_app_cats = GOAL_APP_MAP.get(goal_cat, GOAL_APP_MAP.get("productivity", []))

            if not relevant_app_cats:
                continue  # wellness goals don't map to apps

            # Check which relevant app categories are running
            active_relevant = [c for c in relevant_app_cats if c in running_cats]
            inactive_relevant = [c for c in relevant_app_cats if c not in running_cats]

            # Check for distracting categories
            distracting_cats = ["Browser", "Media", "Communication"]
            active_distractions = {c: running_cats[c] for c in distracting_cats if c in running_cats}
            distraction_mem = sum(d["mem"] for d in active_distractions.values())

            if not active_relevant and goal.current_value < goal.target_value:
                # User has a goal but none of the relevant apps are open
                app_names = ", ".join(relevant_app_cats)
                recs.append({
                    "icon": "🖥️", "priority": "high", "category": "screen-time",
                    "title": f"No Progress on: {goal.title}",
                    "text": f"Your goal \"{goal.title}\" needs {app_names} apps, but none are running. Open the right tools to make progress!",
                })
            elif active_distractions and distraction_mem > 5 and not active_relevant:
                # Spending time on distractions instead of goal-related apps
                distraction_names = ", ".join(active_distractions.keys())
                recs.append({
                    "icon": "📱", "priority": "high", "category": "screen-time",
                    "title": f"Screen Time Mismatch: {goal.title}",
                    "text": f"You're spending time on {distraction_names} ({distraction_mem:.0f}% RAM) but \"{goal.title}\" needs {', '.join(relevant_app_cats)} apps. Consider refocusing.",
                })
            elif active_relevant and active_distractions and distraction_mem > 10:
                # Both relevant and distracting apps running — gentle nudge
                recs.append({
                    "icon": "⚖️", "priority": "medium", "category": "screen-time",
                    "title": f"Balance Your Focus",
                    "text": f"Good — you have {', '.join(active_relevant)} open for \"{goal.title}\". But {', '.join(active_distractions.keys())} might be distracting. Consider minimizing them.",
                })

        # ── General screen time insights ──
        if "Media" in running_cats and running_cats["Media"]["count"] > 0:
            recs.append({
                "icon": "🎵", "priority": "low", "category": "screen-time",
                "title": "Media Apps Active",
                "text": f"Media apps running ({', '.join(running_cats['Media']['apps'][:3])}). Fine for background, but check they're not pulling focus.",
            })

        total_browser = running_cats.get("Browser", {}).get("mem", 0)
        if total_browser > 20:
            recs.append({
                "icon": "🌐", "priority": "medium", "category": "screen-time",
                "title": "High Browser Memory Usage",
                "text": f"Browsers using {total_browser:.0f}% of RAM. Close unused tabs to free resources and reduce distractions.",
            })

        # ── Mood-based recommendations ──
        if mood_score <= 2:
            recs.append({
                "icon": "🧘", "priority": "high", "category": "wellness",
                "title": "Take a Mental Break",
                "text": "Your mood is low. Step away for 10 minutes — stretch, breathe, or grab water.",
            })
        if stress >= 4:
            recs.append({
                "icon": "🎯", "priority": "high", "category": "wellness",
                "title": "Reduce Cognitive Load",
                "text": "High stress detected. Focus on one task at a time. Delegate non-critical work.",
            })
        if energy >= 4 and mood_score >= 4:
            recs.append({
                "icon": "⚡", "priority": "medium", "category": "productivity",
                "title": "Peak Performance Window",
                "text": "High energy + good mood = ideal for deep work! Tackle complex tasks now.",
            })

        # ── Alert-based recommendations ──
        if active_alerts > 10:
            recs.append({
                "icon": "🚨", "priority": "high", "category": "security",
                "title": "Alert Backlog Critical",
                "text": f"{active_alerts} unresolved alerts. Prioritize Critical and High severity first.",
            })
        elif active_alerts > 0:
            recs.append({
                "icon": "🛡️", "priority": "medium", "category": "security",
                "title": "Review Open Alerts",
                "text": f"You have {active_alerts} open alert{'s' if active_alerts != 1 else ''}. Schedule time to triage.",
            })

        # ── Goal-based recommendations ──
        overdue = [g for g in goals if g.deadline and g.deadline < datetime.utcnow()]
        if overdue:
            recs.append({
                "icon": "⏰", "priority": "high", "category": "productivity",
                "title": f"{len(overdue)} Overdue Goal{'s' if len(overdue) > 1 else ''}",
                "text": f"{'Goals' if len(overdue) > 1 else 'Goal'}: {', '.join(g.title for g in overdue[:3])}. Update progress or adjust deadlines.",
            })

        # ── Time-based ──
        hour = datetime.now().hour
        if hour >= 22 or hour < 6:
            recs.append({
                "icon": "🌙", "priority": "medium", "category": "wellness",
                "title": "Late Night Activity",
                "text": "Working late increases error rates. Save complex tasks for tomorrow if possible.",
            })

        if not recs:
            recs.append({
                "icon": "✨", "priority": "low", "category": "general",
                "title": "All Clear",
                "text": "Everything looks good! Stay consistent with mood check-ins and goal updates.",
            })

        return jsonify(recs)
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════════════════
#  EXISTING ENDPOINTS (Dashboard, Alerts, Users, Logs, Analysis)
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/dashboard")
def dashboard():
    session = get_session()
    try:
        total_users    = session.query(User).count()
        active_alerts  = session.query(Alert).filter_by(is_resolved=False).count()
        total_logs     = session.query(ActivityLog).count()
        anomaly_logs   = session.query(ActivityLog).filter_by(is_anomaly=True).count()

        critical = session.query(User).filter_by(risk_level="Critical").count()
        high     = session.query(User).filter_by(risk_level="High").count()
        medium   = session.query(User).filter_by(risk_level="Medium").count()
        low      = session.query(User).filter_by(risk_level="Low").count()

        users = session.query(User).all()
        avg_risk = sum(u.risk_score for u in users) / max(len(users), 1)

        from sqlalchemy import func
        type_counts = (
            session.query(ActivityLog.activity_type, func.count())
            .group_by(ActivityLog.activity_type).all()
        )
        hour_counts = (
            session.query(func.strftime("%H", ActivityLog.timestamp), func.count())
            .group_by(func.strftime("%H", ActivityLog.timestamp)).all()
        )
        alert_trend = (
            session.query(func.date(Alert.timestamp), func.count())
            .group_by(func.date(Alert.timestamp))
            .order_by(func.date(Alert.timestamp)).all()
        )

        return jsonify({
            "total_users": total_users,
            "active_alerts": active_alerts,
            "total_logs": total_logs,
            "anomaly_logs": anomaly_logs,
            "avg_risk_score": round(avg_risk, 1),
            "risk_distribution": {"Critical": critical, "High": high, "Medium": medium, "Low": low},
            "activity_types": {t: c for t, c in type_counts},
            "hourly_activity": {h: c for h, c in hour_counts},
            "alert_trend": [{"date": str(d), "count": c} for d, c in alert_trend],
        })
    finally:
        session.close()


@app.route("/api/alerts")
def get_alerts():
    session = get_session()
    try:
        alerts = session.query(Alert).order_by(Alert.timestamp.desc()).limit(100).all()
        return jsonify([a.to_dict() for a in alerts])
    finally:
        session.close()


@app.route("/api/users")
def get_users():
    session = get_session()
    try:
        users = session.query(User).order_by(User.risk_score.desc()).all()
        return jsonify([u.to_dict() for u in users])
    finally:
        session.close()


@app.route("/api/users/<int:user_id>/activity")
def get_user_activity(user_id):
    session = get_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        activities = (
            session.query(ActivityLog).filter_by(user_id=user_id)
            .order_by(ActivityLog.timestamp.desc()).limit(200).all()
        )
        return jsonify({"user": user.to_dict(), "activities": [a.to_dict() for a in activities]})
    finally:
        session.close()


@app.route("/api/logs")
def get_logs():
    session = get_session()
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        offset = (page - 1) * per_page
        total = session.query(ActivityLog).count()
        logs = (
            session.query(ActivityLog).order_by(ActivityLog.timestamp.desc())
            .offset(offset).limit(per_page).all()
        )
        return jsonify({"total": total, "page": page, "per_page": per_page, "logs": [l.to_dict() for l in logs]})
    finally:
        session.close()


@app.route("/api/analyze", methods=["POST"])
def analyze():
    result = run_analysis()
    return jsonify(result)


# ── Startup ────────────────────────────────────────────────────────────────
def setup():
    """Initialise DB, register local user, and start background monitoring."""
    from realtime import start_scheduler
    
    init_db()
    session = get_session()
    
    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get("USERNAME", os.environ.get("USER", "Unknown"))
        
    user = session.query(User).filter_by(username=username).first()
    if not user:
        print(f"[*] Registering local user: {username}...")
        user = User(
            username=username,
            full_name=username.capitalize(),
            email=f"{username}@local.machine",
            department="Local Machine",
            role="Admin",
            risk_score=0.0,
            risk_level="Low",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(user)
        session.commit()
    
    session.close()
    
    print("[*] Starting real-time activity monitoring...")
    start_scheduler()
    print("[OK] Setup complete!")

if __name__ == "__main__":
    setup()
    app.run(debug=True, host="0.0.0.0", port=5000)
