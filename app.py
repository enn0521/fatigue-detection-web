# 載入套件
import cv2
import os
import time
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, request
from process import DriverFatigueDetector
from config import Config
from state import State
from dotenv import load_dotenv

app = Flask(
    __name__,
    static_folder="assets",
    template_folder="templates"
)

load_dotenv()

# 載入模型
engine = DriverFatigueDetector(
    model_path=str(Config.MODEL_PATH)
)

# 全域狀態
state = State(
    fps=Config.FPS,
    window_sec=Config.WINDOWS_SEC
)

# 全域變數
FLIP_IMAGE = True


def reset_detection_state():
    engine.clear_log(state)

    state.reset_metrics()


# 鏡頭設定
def open_camera(mode="16:9"):
    if state.current_camera is not None:
        try:
            if state.current_camera.isOpened():
                state.current_camera.release()
        except Exception as e:
            print(f"[CAMERA] Release error: {e}")

        state.current_camera = None

    cap = cv2.VideoCapture(
        Config.CAMERA_ID,
        Config.CAMERA_BACKEND
    )

    if not cap.isOpened():
        raise RuntimeError("Camera open failed")

    if mode == "9:16":
        width = Config.PORTRAIT_WIDTH
        height = Config.PORTRAIT_HEIGHT
    else:
        width = Config.LANDSCAPE_WIDTH
        height = Config.LANDSCAPE_HEIGHT

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    print(
        f"[CAMERA] Opened {mode}: "
        f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
        f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
    )

    state.current_camera = cap

    return cap


def generate_frames(mode):
    cap = open_camera(mode)
    prev_frame_time = 0

    print(f"[STREAM] Started: {mode}")

    try:
        while True:
            success, frame = cap.read()

            if not success:
                print("[STREAM] Camera read failed")
                break

            if state.current_camera is not cap:
                print("[STREAM] Old camera detected, stopping...")
                break

            if FLIP_IMAGE:
                frame = cv2.flip(frame, 1)

            new_frame_time = time.perf_counter()

            if state.started:
                result = engine.process_frame(
                    frame,
                    state,
                    draw_landmarks=True
                )

                processed_frame = result["frame"]
            else:
                processed_frame = frame

            # FPS
            if prev_frame_time != 0:
                frame_time = (
                    new_frame_time -
                    prev_frame_time
                )

                if frame_time > 0:
                    state.frame_times.append(frame_time)

                    avg_frame_time = (
                        sum(state.frame_times) /
                        len(state.frame_times)
                    )

                    if avg_frame_time > 0:
                        state.camera_fps = round(1 / avg_frame_time)

            prev_frame_time = new_frame_time

            success, buffer = cv2.imencode(
                ".jpg",
                processed_frame
            )

            if not success:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )

    except GeneratorExit:
        pass

    except Exception as e:
        print(f"[STREAM] Error: {e}")

    finally:
        try:
            if cap.isOpened():
                cap.release()
        except Exception as e:
            print(f"[CAMERA] Release error: {e}")

        if state.current_camera is cap:
            state.current_camera = None


# 路徑設定
@app.route("/")
@app.route("/index")
@app.route("/index.html")
def index():
    return render_template("index.html")


# Video Feed
@app.route("/video_feed")
def video_feed():
    mode = request.args.get("mode", "16:9")

    return Response(
        generate_frames(mode),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# Data API
@app.route("/api/data")
def get_data():
    if not state.started:
        return jsonify({
        "fps": state.camera_fps,
        "latency": round(state.latency),
        "faces": 0,
        "left_ear": None,
        "right_ear": None,
        "ear": None,
        "mar": None,
        "blink_times": 0,
        "yawn_times": 0,
        "eye_closure_dur": 0.0,
        "yawn_dur": 0.0,
        "perclos": 0.0,
        "fatigue_level": "Normal",
        "fatigue_score": 0,
        "ear_threshold": state.ear_threshold,
        "mar_threshold": state.mar_threshold,
        "default_ear_threshold": Config.EAR_CLOSED_THRESHOLD,
        "default_mar_threshold": Config.YAWN_THRESHOLD,      
        "baseline_ear_threshold": state.baseline_ear,
        "baseline_mar_threshold": state.baseline_mar,
        })

    return jsonify({
        "fps": state.camera_fps,
        "latency": round(state.latency),
        "faces": 0,
        "left_ear": None,
        "right_ear": None,
        "ear": None,
        "mar": None,
        "blink_times": 0,
        "yawn_times": 0,
        "eye_closure_dur": 0.0,
        "yawn_dur": 0.0,
        "perclos": 0.0,
        "fatigue_level": "Normal",
        "fatigue_score": 0,
        "ear_threshold": state.ear_threshold,
        "mar_threshold": state.mar_threshold,
        "default_ear_threshold": Config.EAR_CLOSED_THRESHOLD,
        "default_mar_threshold": Config.YAWN_THRESHOLD,      
        "baseline_ear_threshold": state.baseline_ear,
        "baseline_mar_threshold": state.baseline_mar,
    })


@app.route("/start_calibration", methods=["POST"])
def start_calibration():
    if not state.started:
        return jsonify({
            "status": "error",
            "message": "Detection not started"
        }), 400

    state.is_calibrating = True
    state.is_calibrated = False
    state.calibration_ear_samples = []
    state.calibration_mar_samples = []

    return jsonify({
        "status": "calibrating",
        "target_frames": Config.CALIBRATION_FRAMES
    })


@app.route("/calibration_status")
def calibration_status():
    return jsonify({
        "is_calibrating": state.is_calibrating,
        "is_calibrated": state.is_calibrated,
        "progress": len(state.calibration_ear_samples),
        "target": Config.CALIBRATION_FRAMES,
        "baseline_ear_threshold": state.baseline_ear,
        "baseline_mar_threshold": state.baseline_mar,
        "ear_threshold": state.ear_threshold,
        "mar_threshold": state.mar_threshold,
    })


@app.route("/select_calibration", methods=["POST"])
def select_calibration():
    mode = (request.get_json(silent=True) or {}).get("mode")

    if mode == "baseline":
        if not state.is_calibrated:
            return jsonify({
                "status": "error",
                "message": "Not calibrated yet"
            }), 400

        state.ear_threshold = round(
            state.baseline_ear * Config.CALIBRATION_EAR_RATIO, 4
        )

        if state.baseline_mar is not None:
            state.mar_threshold = round(
                state.baseline_mar + Config.CALIBRATION_MAR_OFFSET, 4
            )

    elif mode == "default":
        state.ear_threshold = Config.EAR_CLOSED_THRESHOLD
        state.mar_threshold = Config.YAWN_THRESHOLD

    else:
        return jsonify({
            "status": "error",
            "message": "Invalid mode"
        }), 400

    return jsonify({
        "status": "ok",
        "ear_threshold": state.ear_threshold,
        "mar_threshold": state.mar_threshold,
    })


# Start Detection
@app.route("/start_detection", methods=["POST"])
def start_detection():
    if state.started:
        return jsonify({
            "started": True,
            "status": "already_started"
        })

    reset_detection_state()

    state.started = True

    print("[DETECTION] Started")

    return jsonify({
        "started": True,
        "status": "started"
    })


# Stop Detection
@app.route("/stop_detection", methods=["POST"])
def stop_detection():
    if not state.started:
        return jsonify({
            "started": False,
            "status": "already_stopped"
        })

    engine.record_log(
        state,
        {
            "ear": state.ear,
            "mar": state.mar,
            "left_ear": state.left_ear,
            "right_ear": state.right_ear
        },
        state.face_count,
        event="pause"
    )

    state.started = False

    state.reset_metrics()

    return jsonify({
        "started": False,
        "status": "stopped"
    })


# Reset Detection
@app.route("/reset", methods=["POST"])
def reset_detection():
    reset_detection_state()

    print("[DETECTION] Reset")

    return jsonify({
        "status": "reset",
        "started": state.started,
        "ear_threshold": Config.EAR_CLOSED_THRESHOLD,
        "mar_threshold": Config.YAWN_THRESHOLD,
    })


# Detection Status
@app.route("/detection_status")
def detection_status():
    return jsonify({
        "started": state.started
    })


# Export CSV
@app.route("/export_csv")
def export_csv():
    csv_data = engine.export_csv(state)

    filename = (
        f"log_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 5000)),
        debug=True,
        threaded=True
    )