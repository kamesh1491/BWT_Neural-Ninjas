from apscheduler.schedulers.background import BackgroundScheduler
from ml_engine import run_analysis
from models import get_session, User, ActivityLog
import psutil
from datetime import datetime
import socket
import os

scheduler = BackgroundScheduler()

# App category mapping for identifying what type of app is running
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

def _categorize_app(name):
    name_lower = name.lower().replace(".exe", "")
    for key, cat in APP_CATEGORIES.items():
        if key in name_lower:
            return cat
    return "System"

# Global state to track process activity between intervals
_last_seen_procs = set()

def collect_real_activity():
    """Poll system processes to see what the user is actively doing."""
    global _last_seen_procs
    
    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get("USERNAME", os.environ.get("USER", "Unknown"))
        
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return # User not initialized yet
            
        current_procs = set()
        new_activities = []
        
        # We look for apps that use notable CPU or Memory to indicate active usage
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                name = info["name"] or "Unknown"
                
                # Ignore system processes for logging
                cat = _categorize_app(name)
                if cat == "System":
                    continue
                    
                pid = info["pid"]
                current_procs.add(pid)
                
                # If this is a new process we haven't seen recently:
                if pid not in _last_seen_procs:
                    desc = f"Opened {cat} app: {name}"
                    new_activities.append(
                        ActivityLog(
                            user_id=user.id,
                            timestamp=datetime.utcnow(),
                            activity_type=cat.lower().replace(" ", "_"),
                            description=desc,
                            ip_address="127.0.0.1",
                            device=socket.gethostname(),
                            location="Local Machine"
                        )
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # Bulk insert new activities
        if new_activities:
            session.add_all(new_activities)
            session.commit()
            print(f"[Realtime] Logged {len(new_activities)} new app activities.")
            
        _last_seen_procs = current_procs

    except Exception as e:
        print(f"[Realtime] Error collecting activity: {e}")
    finally:
        session.close()

def scheduled_analysis():
    print("[Realtime] Running ML anomaly detection...")
    result = run_analysis()
    print(f"[Realtime] Analysis complete: {result}")

def start_scheduler():
    scheduler.add_job(collect_real_activity, "interval", minutes=1)
    scheduler.add_job(scheduled_analysis, "interval", minutes=5)
    scheduler.start()
