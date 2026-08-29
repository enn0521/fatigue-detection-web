from collections import deque
import time
from config import Config


class State:

    def __init__(self, fps=30, window_sec=5):
        self.fps = fps
        self.window_size = fps * window_sec

        self.reset()

    def reset(self):

        self.started = False

        self.current_camera = None
        self.camera_fps = 0
        self.latency = 0
        self.frame_times = deque(maxlen=max(self.fps, 1))

        self.face_count = 0

        self.left_ear = None
        self.right_ear = None
        self.ear = None

        self.blink_times = 0
        self.eye_closure_frames = 0
        self.eye_closure_dur = 0.0
        self.is_eye_closed = False

        self.mar = None
        self.yawn_times = 0
        self.yawn_dur = 0.0
        self.is_yawning = False
        self.yawning_start_time = None

        self.nod_ratio = 0.0
        self.is_nodding = False
        self.nodding_start_time = None

        self.perclos = 0.0
        self.eye_closure_history = deque(maxlen=self.window_size)

        self.fatigue_level = "Normal"
        self.fatigue_score = 0

        self.log_history = []
        self.last_log_time = 0.0

        self.last_alert_time = None
        self.alert_count = 0
        self.is_alert_active = False
        self.alert_history = []

        self.is_calibrated = False
        self.is_calibrating = False
        self.calibration_ear_samples = []
        self.calibration_mar_samples = []
        self.baseline_ear = None
        self.baseline_mar = None

        self.ear_threshold = Config.EAR_CLOSED_THRESHOLD
        self.mar_threshold = Config.YAWN_THRESHOLD

        self.start_record_time = time.time()

    def reset_metrics(self):

        self.latency = 0
        self.face_count = 0

        self.left_ear = None
        self.right_ear = None
        self.ear = None
        self.mar = None

        self.blink_times = 0
        self.yawn_times = 0

        self.eye_closure_frames = 0
        self.eye_closure_dur = 0.0
        self.is_eye_closed = False

        self.yawn_dur = 0.0
        self.is_yawning = False
        self.yawning_start_time = None

        self.perclos = 0.0
        self.eye_closure_history.clear()

        self.fatigue_level = "Normal"
        self.fatigue_score = 0

        self.start_record_time = time.time()