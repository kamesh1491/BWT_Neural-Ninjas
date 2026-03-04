
def generate_threat_map(logs):
    locations = []
    for log in logs:
        if log.get("is_anomaly"):
            locations.append({
                "ip": log.get("ip"),
                "location": log.get("location"),
                "timestamp": log.get("timestamp")
            })
    return locations
