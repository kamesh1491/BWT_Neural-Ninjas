"""
ML Anomaly Detection Engine for Insider Threat Detection.
Uses Isolation Forest to detect behavioural anomalies in user activity.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
from models import get_session, User, ActivityLog, Alert


def extract_features(session):
    """
    Build a feature matrix from activity logs.
    Each row = one user, columns = behavioural features.
    Returns (user_ids, feature_df).
    """
    users = session.query(User).all()
    if not users:
        return [], pd.DataFrame()

    records = []
    for user in users:
        logs = session.query(ActivityLog).filter_by(user_id=user.id).all()
        if not logs:
            continue

        timestamps = [l.timestamp for l in logs]
        hours = [t.hour for t in timestamps]

        # ---- Feature engineering ----
        total_activities    = len(logs)
        login_count         = sum(1 for l in logs if l.activity_type == "login")
        failed_logins       = sum(1 for l in logs if l.activity_type == "failed_login")
        file_accesses       = sum(1 for l in logs if l.activity_type == "file_access")
        usb_events          = sum(1 for l in logs if l.activity_type == "usb_usage")
        email_events        = sum(1 for l in logs if l.activity_type == "email")

        # After‑hours ratio (before 7 AM or after 8 PM)
        after_hours = sum(1 for h in hours if h < 7 or h > 20)
        after_hours_ratio = after_hours / max(total_activities, 1)

        # Average login hour & std deviation
        login_hours = [t.hour for t in timestamps
                       if any(l.timestamp == t and l.activity_type == "login" for l in logs)]
        avg_login_hour = np.mean(login_hours) if login_hours else 12
        std_login_hour = np.std(login_hours)  if login_hours else 0

        # Failed login ratio
        failed_ratio = failed_logins / max(login_count + failed_logins, 1)

        # Unique devices
        devices = set(l.device for l in logs if l.device)
        unique_devices = len(devices)

        # Unique IPs
        ips = set(l.ip_address for l in logs if l.ip_address)
        unique_ips = len(ips)

        # Weekend activity ratio
        weekend = sum(1 for t in timestamps if t.weekday() >= 5)
        weekend_ratio = weekend / max(total_activities, 1)

        # File access burst — max file accesses in any single hour
        file_ts = [l.timestamp for l in logs if l.activity_type == "file_access"]
        file_burst = 0
        if file_ts:
            file_hours = {}
            for t in file_ts:
                key = t.strftime("%Y-%m-%d-%H")
                file_hours[key] = file_hours.get(key, 0) + 1
            file_burst = max(file_hours.values())

        records.append({
            "user_id":           user.id,
            "total_activities":  total_activities,
            "login_count":       login_count,
            "failed_logins":     failed_logins,
            "failed_ratio":      failed_ratio,
            "file_accesses":     file_accesses,
            "file_burst":        file_burst,
            "usb_events":        usb_events,
            "email_events":      email_events,
            "after_hours_ratio": after_hours_ratio,
            "avg_login_hour":    avg_login_hour,
            "std_login_hour":    std_login_hour,
            "unique_devices":    unique_devices,
            "unique_ips":        unique_ips,
            "weekend_ratio":     weekend_ratio,
        })

    df = pd.DataFrame(records)
    user_ids = df["user_id"].tolist()
    feature_cols = [c for c in df.columns if c != "user_id"]
    return user_ids, df[feature_cols]


def run_analysis():
    """
    Run anomaly detection and update the database with results.
    Returns summary dict.
    """
    session = get_session()

    try:
        user_ids, features = extract_features(session)
        if features.empty:
            return {"status": "no_data", "anomalies": 0}

        # Standardise features
        scaler = StandardScaler()
        X = scaler.fit_transform(features)

        # Isolation Forest — contamination estimates ~15 % anomalies
        if len(X) >= 5:
            model = IsolationForest(
                n_estimators=200,
                contamination=0.15,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(X)
            predictions  = model.predict(X)           # 1 = normal, -1 = anomaly
            scores_raw   = model.decision_function(X)  # lower = more anomalous
            
            # Map decision‑function scores → 0‑100 risk score
            min_s, max_s = scores_raw.min(), scores_raw.max()
            if max_s - min_s == 0:
                risk_scores = [50.0] * len(scores_raw)
            else:
                risk_scores = [
                    round(float((1 - (s - min_s) / (max_s - min_s)) * 100), 1)
                    for s in scores_raw
                ]
        else:
            # Not enough data for Isolation Forest, fallback to heuristics
            predictions = np.ones(len(X))
            risk_scores = []
            for idx in range(len(X)):
                feat = features.iloc[idx]
                score = 10.0
                if feat.get("after_hours_ratio", 0) > 0.3: score += 20
                if feat.get("failed_ratio", 0) > 0.2: score += 30
                if feat.get("usb_events", 0) > 2: score += 20
                if feat.get("weekend_ratio", 0) > 0.3: score += 10
                if feat.get("file_burst", 0) > 10: score += 20
                risk_scores.append(min(100.0, score))
                if score >= 60:
                    predictions[idx] = -1

        anomalies_found = 0

        for idx, uid in enumerate(user_ids):
            user = session.query(User).get(uid)
            if not user:
                continue

            risk = risk_scores[idx]
            user.risk_score = risk

            if risk >= 80:
                user.risk_level = "Critical"
            elif risk >= 60:
                user.risk_level = "High"
            elif risk >= 40:
                user.risk_level = "Medium"
            else:
                user.risk_level = "Low"

            # Generate alerts for anomalous users
            if predictions[idx] == -1:
                anomalies_found += 1
                _generate_alerts(session, user, features.iloc[idx], risk)

            # Mark individual anomalous logs
            _mark_anomalous_logs(session, user, model, scaler, features.columns.tolist())

        session.commit()
        return {"status": "success", "anomalies": anomalies_found, "total_users": len(user_ids)}

    finally:
        session.close()


def _generate_alerts(session, user, feats, risk):
    """Create Alert rows for specific anomaly categories."""
    now = datetime.utcnow()
    severity = "Critical" if risk >= 80 else "High" if risk >= 60 else "Medium"

    # After‑hours activity
    if feats.get("after_hours_ratio", 0) > 0.3:
        session.add(Alert(
            user_id=user.id, timestamp=now, severity=severity,
            category="odd_hour_login",
            title=f"Unusual after‑hours activity detected for {user.full_name}",
            description=(
                f"{user.full_name} has {feats['after_hours_ratio']:.0%} of activity "
                "outside normal working hours (before 7 AM or after 8 PM)."
            ),
        ))

    # Excessive file access
    if feats.get("file_burst", 0) > 10:
        session.add(Alert(
            user_id=user.id, timestamp=now, severity=severity,
            category="excessive_file_access",
            title=f"Excessive file access burst by {user.full_name}",
            description=(
                f"{user.full_name} accessed {int(feats['file_burst'])} files in a single "
                "hour, significantly above normal behaviour."
            ),
        ))

    # Failed login spike
    if feats.get("failed_ratio", 0) > 0.25:
        session.add(Alert(
            user_id=user.id, timestamp=now, severity=severity,
            category="failed_login_spike",
            title=f"High failed‑login ratio for {user.full_name}",
            description=(
                f"{feats['failed_ratio']:.0%} of {user.full_name}'s login attempts "
                "have failed, suggesting credential abuse or brute‑force attempts."
            ),
        ))

    # USB / removable device usage
    if feats.get("usb_events", 0) > 5:
        session.add(Alert(
            user_id=user.id, timestamp=now, severity=severity,
            category="unauthorized_device",
            title=f"Frequent USB device usage by {user.full_name}",
            description=(
                f"{user.full_name} has {int(feats['usb_events'])} USB device events "
                "recorded, which may indicate data exfiltration attempts."
            ),
        ))

    # Weekend activity
    if feats.get("weekend_ratio", 0) > 0.25:
        session.add(Alert(
            user_id=user.id, timestamp=now, severity=severity,
            category="weekend_activity",
            title=f"Significant weekend activity for {user.full_name}",
            description=(
                f"{feats['weekend_ratio']:.0%} of {user.full_name}'s activity occurs on "
                "weekends, which may warrant investigation."
            ),
        ))


def _mark_anomalous_logs(session, user, model, scaler, feature_cols):
    """Set is_anomaly on individual activity log entries for a user."""
    logs = session.query(ActivityLog).filter_by(user_id=user.id).all()
    for log in logs:
        # Simple heuristic: mark after‑hours + unusual types
        hour = log.timestamp.hour if log.timestamp else 12
        is_odd_hour = hour < 6 or hour > 22
        is_sensitive = log.activity_type in ("usb_usage", "failed_login")
        if is_odd_hour or is_sensitive:
            log.is_anomaly = True
            log.anomaly_score = round(min(0.5 + (0.3 if is_odd_hour else 0) + (0.2 if is_sensitive else 0), 1.0), 3)
        else:
            log.is_anomaly = False
            log.anomaly_score = 0.0
