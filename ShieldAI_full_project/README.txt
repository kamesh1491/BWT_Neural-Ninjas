
ShieldAI – Insider Threat Detection Platform

Structure:

backend/
    app.py
    ml_engine.py
    models.py
    seed_data.py
    realtime.py
    ai_explainer.py
    threat_map.py
    requirements.txt

static/
    index.html
    css/style.css
    js/app.js

Setup:

1) Install dependencies
pip install -r backend/requirements.txt
pip install flask-socketio apscheduler

2) Run server
cd backend
python app.py

3) Open dashboard
http://localhost:5000

Features:
• AI anomaly detection
• insider threat monitoring
• SOC dashboard
• user behaviour analytics
• mood & productivity insights
• live system monitoring
