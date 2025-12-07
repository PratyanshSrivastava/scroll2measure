#!/usr/bin/env python3
from flask import Flask, render_template_string, jsonify
from pynput import mouse
import threading

app = Flask(__name__)

# Shared state
scroll_count = 0
clicks_per_cm = None   # set after calibration
mode = "idle"          # "idle", "calibrate", "measure"
listener = None
lock = threading.Lock()

def on_scroll(x, y, dx, dy):
    global scroll_count
    with lock:
        scroll_count += abs(dy)

def start_listener(new_mode):
    global listener, mode, scroll_count
    with lock:
        if listener is not None:
            return
        scroll_count = 0
        mode = new_mode

    def run():
        global listener, mode
        with mouse.Listener(on_scroll=on_scroll) as l:
            listener = l
            l.join()
        with lock:
            listener = None
            mode = "idle"

    t = threading.Thread(target=run, daemon=True)
    t.start()

def stop_listener():
    global listener, mode
    with lock:
        if listener is not None:
            listener.stop()
            listener = None
        mode = "idle"

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/start_calibration")
def api_start_calibration():
    start_listener("calibrate")
    return jsonify({"status": "ok"})

@app.route("/api/finish_calibration")
def api_finish_calibration():
    global clicks_per_cm
    stop_listener()
    with lock:
        if scroll_count == 0:
            return jsonify({"status": "error", "msg": "No scroll detected"}), 400
        # 30 cm reference
        clicks_per_cm = scroll_count / 30.0
        ratio = clicks_per_cm
        clicks = scroll_count
    return jsonify({
        "status": "ok",
        "clicks": clicks,
        "clicks_per_cm": ratio,
        "cm_per_click": 1.0 / ratio
    })

@app.route("/api/start_measure")
def api_start_measure():
    if clicks_per_cm is None:
        return jsonify({"status": "error", "msg": "Not calibrated"}), 400
    start_listener("measure")
    return jsonify({"status": "ok"})

@app.route("/api/stop_measure")
def api_stop_measure():
    stop_listener()
    return jsonify({"status": "ok"})

@app.route("/api/reset")
def api_reset():
    global scroll_count
    with lock:
        scroll_count = 0
    return jsonify({"status": "ok"})

@app.route("/api/status")
def api_status():
    with lock:
        clicks = scroll_count
        current_mode = mode
        ratio = clicks_per_cm

    if ratio:
        distance_cm = clicks / ratio
        distance_mm = distance_cm * 10
        distance_m = distance_cm / 100
        distance_in = distance_cm / 2.54
    else:
        distance_cm = distance_mm = distance_m = distance_in = 0.0

    return jsonify({
        "clicks": clicks,
        "mode": current_mode,
        "calibrated": ratio is not None,
        "clicks_per_cm": round(ratio, 4) if ratio else None,
        "distance_cm": round(distance_cm, 2),
        "distance_mm": round(distance_mm, 1),
        "distance_m": round(distance_m, 3),
        "distance_in": round(distance_in, 2)
    })

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MouseTape Flask</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #fafaf8;
            color: #134252;
            margin: 0;
            padding: 20px;
        }
        .card {
            max-width: 640px;
            margin: 0 auto;
            background: #fff;
            border-radius: 12px;
            border: 1px solid #e8e8e6;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        h1 { margin-top: 0; }
        .subtitle { color: #627C71; font-size: 14px; margin-bottom: 16px; }
        .distance {
            font-size: 32px;
            font-weight: 700;
            color: #2B8080;
            margin: 12px 0;
        }
        .sub { font-size: 13px; color: #627C71; }
        button {
            padding: 10px 18px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            margin-right: 8px;
            margin-top: 8px;
        }
        .primary { background: #218D8D; color: white; }
        .secondary { background: #f5f5f5; color: #134252; }
        .danger { background: #C0152F; color: white; }
        .row { margin-top: 12px; }
        .tag {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 600;
            background: rgba(33,141,141,0.08);
            color: #218D8D;
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
<div class="card">
    <h1>🖱️ Scroll2Measure Flask</h1>
    <p class="subtitle">Calibrate with 30 cm, then measure in real time.</p>

    <div id="status-tag" class="tag">Idle</div>

    <div class="distance" id="distance-main">0.00 cm</div>
    <div class="sub" id="distance-extra">0.0 mm · 0.000 m · 0.00 in</div>
    <div class="sub" id="clicks-label">Clicks: 0</div>
    <div class="sub" id="calib-label">Not calibrated</div>

    <div class="row">
        <strong>Calibration (30 cm):</strong><br>
        <button class="primary" id="btn-calib-start">Start Calibration</button>
        <button class="secondary" id="btn-calib-finish">Finish Calibration</button>
    </div>

    <div class="row">
        <strong>Measurement:</strong><br>
        <button class="primary" id="btn-meas-start">Start Measuring</button>
        <button class="secondary" id="btn-meas-stop">Stop Measuring</button>
        <button class="secondary" id="btn-reset">Reset Distance</button>
    </div>

    <p class="sub" style="margin-top:16px;">
        Calibration instructions: place mouse on a flat surface, mark 30 cm with a ruler,
        click <strong>Start Calibration</strong> and roll the scroll wheel exactly from 0 to 30 cm,
        then click <strong>Finish Calibration</strong>.
    </p>
    <p class="sub">
        Measurement: click <strong>Start Measuring</strong>, roll the wheel over what you want to measure,
        watch the distance update in real time, then click <strong>Stop Measuring</strong>.
    </p>
</div>

<script>
    async function callApi(path) {
        const res = await fetch(path);
        return await res.json();
    }

    function setStatus(text) {
        document.getElementById("status-tag").textContent = text;
    }

    async function updateStatus() {
        const data = await callApi("/api/status");
        document.getElementById("distance-main").textContent =
            data.distance_cm.toFixed(2) + " cm";
        document.getElementById("distance-extra").textContent =
            data.distance_mm.toFixed(1) + " mm · " +
            data.distance_m.toFixed(3) + " m · " +
            data.distance_in.toFixed(2) + " in";
        document.getElementById("clicks-label").textContent =
            "Clicks: " + data.clicks;

        if (data.calibrated) {
            document.getElementById("calib-label").textContent =
                "Calibrated: " + data.clicks_per_cm.toFixed(2) + " clicks/cm";
        } else {
            document.getElementById("calib-label").textContent = "Not calibrated";
        }
        setStatus("Mode: " + data.mode);
    }

    document.getElementById("btn-calib-start").onclick = async () => {
        await callApi("/api/start_calibration");
        setStatus("Calibrating... Roll 30 cm");
    };

    document.getElementById("btn-calib-finish").onclick = async () => {
        const res = await fetch("/api/finish_calibration");
        if (!res.ok) {
            alert("Calibration failed (no scroll?). Try again.");
        } else {
            const data = await res.json();
            alert(
                "Calibration done!\\nClicks: " + data.clicks +
                "\\nClicks/cm: " + data.clicks_per_cm.toFixed(2) +
                "\\ncm/click: " + data.cm_per_click.toFixed(4)
            );
        }
        await updateStatus();
    };

    document.getElementById("btn-meas-start").onclick = async () => {
        const res = await fetch("/api/start_measure");
        if (!res.ok) {
            const data = await res.json();
            alert("Error: " + (data.msg || "Not calibrated"));
            return;
        }
        setStatus("Measuring... Roll wheel");
    };

    document.getElementById("btn-meas-stop").onclick = async () => {
        await callApi("/api/stop_measure");
        setStatus("Idle");
        await updateStatus();
    };

    document.getElementById("btn-reset").onclick = async () => {
        await callApi("/api/reset");
        await updateStatus();
    };

    setInterval(updateStatus, 100);
    updateStatus();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("MouseTape Flask running on http://127.0.0.1:5000")
    app.run(debug=True)
