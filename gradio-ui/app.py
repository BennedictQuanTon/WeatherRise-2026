import gradio as gr
import requests
import time
from datetime import datetime, timedelta

BACKEND_URL = "http://localhost:8008"

# --- API Helpers ---
def get_destinations():
    try:
        res = requests.get(f"{BACKEND_URL}/destinations")
        if res.status_code == 200 and res.json().get("success"):
            return {d['name']: d['destination_id'] for d in res.json()['data']}
    except Exception:
        pass
    return {"Son Tra Peninsula": "danang_son_tra_peninsula"}

def analyze_weather(destination_id, date_val, time_val, monitor, alert_channel, phone_number):
    try:
        req = {
            "destination_id": destination_id,
            "forecast_date": date_val,
            "forecast_time": time_val,
            "monitoring_enabled": monitor,
            "alert_channel": alert_channel,
            "phone_number": phone_number
        }
        res = requests.post(f"{BACKEND_URL}/weather/analyze", json=req)
        if res.status_code == 200:
            payload = res.json()
            if not payload.get("success"):
                return f"Backend Error: {payload.get('error', {}).get('message')}", ""
                
            data = payload['data']
            meta = payload.get('meta', {})
            
            # If monitoring is enabled, we need to register the session
            session_id = "None"
            if monitor:
                sess_req = {
                    "session_id": f"sess_{int(time.time())}",
                    "destination_id": destination_id,
                    "forecast_date": date_val,
                    "forecast_time": time_val,
                    "alert_channel": alert_channel,
                    "phone_number": phone_number,
                    "last_risk_overall": data['risk']['overall'],
                    "is_active": True
                }
                sess_res = requests.post(f"{BACKEND_URL}/session/register", json=sess_req)
                if sess_res.status_code == 200 and sess_res.json().get("success"):
                    session_id = sess_res.json()['data']["session_id"]

            mon_status = "🟢 Active" if session_id != "None" else "⚪ Disabled"
            src = meta.get('source', 'Unknown')
            
            md_output = f"""
            ### 📍 {data['location']}
            
            **Overall Risk:** {data['risk']['overall'].upper()}
            - 🌧️ Rain: {data['risk']['rain']}
            - 🌡️ Heat: {data['risk']['heat']}
            - 💨 Wind: {data['risk']['wind']}
            
            **Impact:** {data['impact']}
            **Recommendation:** {data['recommendation']}
            
            ---
            *Source: {src} | Monitoring: {mon_status}*
            """
            return md_output, session_id
    except Exception as e:
        return f"Error connecting to backend: {e}", ""
    return "Failed to analyze weather", ""

def simulate_conflict(session_id):
    if not session_id or session_id == "None":
        return "No active session ID provided."
    try:
        res = requests.post(f"{BACKEND_URL}/watcher/simulate-conflict?session_id={session_id}")
        if res.status_code == 200:
            payload = res.json()
            if payload.get("success"):
                alert = payload["data"]["alert"]
                return f"⚠️ **ALERT**: {alert['message']}\n\n**New Recommendation**: {alert['new_recommendation']}"
            else:
                return f"Error: {payload.get('error', {}).get('message')}"
    except Exception as e:
        return f"Error connecting to backend: {e}"
    return "Failed to simulate conflict"

# --- Gradio UI Construction ---
dest_map = get_destinations()
dest_names = list(dest_map.keys())

today = datetime.now()
dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
times = [f"{str(i).zfill(2)}:00" for i in range(6, 23)] # 6am to 10pm

with gr.Blocks(theme=gr.themes.Soft(), title="Weatherise MVP") as demo:
    gr.Markdown("# 🌦️ Weatherise Intelligence")
    gr.Markdown("Select a destination in Da Nang to analyze weather risks and get proactive recommendations.")
    
    with gr.Row():
        with gr.Column(scale=2):
            dest_dropdown = gr.Dropdown(choices=dest_names, label="Destination", value=dest_names[0] if dest_names else None)
            
            with gr.Row():
                date_dropdown = gr.Dropdown(choices=dates, label="Date", value=dates[1]) # Default to tomorrow
                time_dropdown = gr.Dropdown(choices=times, label="Time", value="18:00")
                
            with gr.Row():
                monitor_toggle = gr.Checkbox(label="Enable Real-time Monitoring", value=True)
                channel_dropdown = gr.Dropdown(choices=["ui_banner", "sms"], label="Notification Channel", value="ui_banner")
            
            phone_input = gr.Textbox(label="Phone Number (for SMS)", placeholder="+84...", visible=False)
            submit_btn = gr.Button("Analyze Weather Risk", variant="primary")
            
            def toggle_phone(channel):
                return gr.update(visible=channel == "sms")
                
            channel_dropdown.change(toggle_phone, inputs=channel_dropdown, outputs=phone_input)
            
        with gr.Column(scale=3):
            result_md = gr.Markdown("### Results will appear here")
            
    gr.Markdown("---")
    
    with gr.Accordion("Developer / Judge Tools (Simulate Alert Workflow)", open=False):
        gr.Markdown("Use this panel to simulate a sudden worsening of weather conditions for an active session.")
        session_id_state = gr.Textbox(label="Active Session ID", interactive=False)
        simulate_btn = gr.Button("🚨 Simulate Weather Conflict (Triggers Watcher Agent)", variant="stop")
        alert_output = gr.Markdown("")
        
    # Wire up events
    def on_submit(dest_name, d, t, m, c, p):
        dest_id = dest_map.get(dest_name, "")
        result, sess_id = analyze_weather(dest_id, d, t, m, c, p)
        return result, sess_id

    submit_btn.click(on_submit, inputs=[dest_dropdown, date_dropdown, time_dropdown, monitor_toggle, channel_dropdown, phone_input], outputs=[result_md, session_id_state])
    simulate_btn.click(simulate_conflict, inputs=[session_id_state], outputs=[alert_output])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
