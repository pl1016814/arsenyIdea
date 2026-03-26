import cv2
import time
import threading
import requests
import numpy as np
from flask import Flask, Response
from flask_cors import CORS
from LineDetector import LineDetector

app = Flask(__name__)
CORS(app)

HOST_IP    = '0.0.0.0'
PORT       = 8080
STREAM_URL = "http://192.168.240.150:8080/video_feed"
ROBOT_URL  = "http://192.168.240.150:8080"

line_detector = LineDetector()
last_frame = None
lock = threading.Lock()

last_seen_error = 0

def update_camera():
    global last_frame
    cap = cv2.VideoCapture(STREAM_URL)

    while True:
        success, frame = cap.read()

        if not success:
            print("Lost connection to camera. Reconnecting...")
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(STREAM_URL)
            continue

        with lock:
            last_frame = frame.copy()

threading.Thread(target=update_camera, daemon=True).start()


def send_command(cmd):
    try:
        requests.post(f"{ROBOT_URL}/move/{cmd}", timeout=1)
        print(f"Sent: {cmd}")
    except:
        print(f"Failed to send: {cmd}")


def send_pwm(left, right):
    try:
        requests.post(
            f"{ROBOT_URL}/move_pwm",
            json={"left": left, "right": right},
            timeout=1
        )
    except:
        print("PWM send failed")


BASE_SPEED = 50
Kp = 0.15

LEFT_TRIM  = 1.0
RIGHT_TRIM = 0.35

DEAD_ZONE = 10
SEARCH_FAST = 34
SEARCH_SLOW = 20


def get_lane_center_from_mask(mask):
    h, w = mask.shape
    y = int(h * 0.8)   # смотрим нижнюю часть кадра

    row = mask[y]

    xs = np.where(row > 0)[0]

    if len(xs) < 2:
        return None

    center_screen = w // 2

    left_candidates = xs[xs < center_screen]
    right_candidates = xs[xs > center_screen]

    if len(left_candidates) == 0 or len(right_candidates) == 0:
        return None

    left_x = np.max(left_candidates)
    right_x = np.min(right_candidates)

    lane_center = (left_x + right_x) / 2
    return lane_center


def control_loop():
    global last_seen_error

    while True:
        time.sleep(0.05)

        with lock:
            if last_frame is None:
                continue
            frame = last_frame.copy()

        try:
            optimized = line_detector.optimize_frame(frame)
            transformed = line_detector.transform(optimized)
            mask = line_detector.threshold_img(transformed)
            morphed = line_detector.Morphology(mask)

            lane_center = get_lane_center_from_mask(morphed)

            if lane_center is None:
                raise ValueError("Two lane borders not found")

            center_of_screen = transformed.shape[1] / 2
            error = lane_center - center_of_screen

            if abs(error) < DEAD_ZONE:
                error = 0

            if error != 0:
                last_seen_error = error

            left_speed  = (BASE_SPEED + (Kp * error)) * LEFT_TRIM
            right_speed = (BASE_SPEED - (Kp * error)) * RIGHT_TRIM

            left_speed  = max(-70, min(70, left_speed))
            right_speed = max(-100, min(100, right_speed))

            print(f"lane_center={lane_center:.1f}, error={error:.1f}, last_seen_error={last_seen_error:.1f}")

            send_pwm(left_speed, right_speed)

        except Exception as e:
            print(f"LINE LOST -> SEARCH MODE: {e}")

            if last_seen_error > 0:
                send_pwm(SEARCH_FAST, SEARCH_SLOW)
            elif last_seen_error < 0:
                send_pwm(SEARCH_SLOW, SEARCH_FAST)
            else:
                send_command("stop")

threading.Thread(target=control_loop, daemon=True).start()


def generate_frames(processed=False):
    while True:
        with lock:
            if last_frame is None:
                time.sleep(0.05)
                continue

            frame = last_frame.copy()

        if processed:
            frame = line_detector.process_frame(frame)

        ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               buffer.tobytes() +
               b'\r\n')

        time.sleep(0.033)


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/video_feed/processed')
def video_feed_processed():
    return Response(
        generate_frames(processed=True),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


if __name__ == '__main__':
    app.run(host=HOST_IP, port=PORT, threaded=True)

"""Archetecture:
*   config.py # все константы  
*   camera.py  # *CameraStream*
*   lane_detector.py  # обёртка над LineDetector + multi-row
*   robot_client.py   # PD контроллер
*   pid_controller.py  # HTTP команды к роботу
*   control_loop.py  # основная логика + stop/search/run
*   app.py  # только Flask routes    



"""
