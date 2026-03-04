
def explain_anomaly(user, features):
    reasons = []
    if features.get("after_hours_ratio",0) > 0.3:
        reasons.append("High activity outside working hours")
    if features.get("failed_ratio",0) > 0.25:
        reasons.append("Large number of failed logins")
    if features.get("file_burst",0) > 10:
        reasons.append("Excessive file access burst")
    if features.get("usb_events",0) > 5:
        reasons.append("Frequent USB usage")

    return {
        "user": user,
        "risk_score": features.get("risk_score"),
        "reasons": reasons
    }
