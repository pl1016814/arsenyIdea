import time, threading
from config import Config

class RobotState:
    STOPPED  = "stopped"
    RUNNING  = "running"
    SEARCHING = "searching"

class ControlLoop:
    def __init__(self, camera, detector, pid, robot, config: Config):
        self._camera   = camera
        self._detector = detector
        self._pid      = pid
        self._robot    = robot
        self._cfg      = config

        self._state           = RobotState.STOPPED
        self._lost_frames     = 0
        self._last_seen_error = 0
        self._lock            = threading.Lock()

    @property
    def state(self):
        return self._state

    def _compute_speeds(self, error):
        # adaptive speed: быстрее на прямой, медленнее на повороте
        turn_factor = 1.0 - min(abs(error) / 150.0, 0.5)
        base        = self._cfg.base_speed * turn_factor

        output      = self._pid.compute(error)
        left  = (base + output) * self._cfg.left_trim
        right = (base - output) * self._cfg.right_trim

        left  = max(-self._cfg.max_speed, min(self._cfg.max_speed, left))
        right = max(-self._cfg.max_speed, min(self._cfg.max_speed, right))
        return left, right

    def step(self):
        frame = self._camera.get_frame()
        if frame is None:
            return

        try:
            transformed, morphed = self._detector.process(frame)
            lane_center          = self._detector.get_lane_center(morphed)

            if lane_center is None:
                raise ValueError("No lane")

            # линия найдена
            self._lost_frames = 0
            self._state       = RobotState.RUNNING

            width = transformed.shape[1]
            error = lane_center - width / 2

            if abs(error) < self._cfg.dead_zone:
                error = 0
            if error != 0:
                self._last_seen_error = error

            left, right = self._compute_speeds(error)
            self._robot.send_pwm(left, right)

        except Exception:
            self._lost_frames += 1

            if self._lost_frames >= self._cfg.lost_threshold:
                # долго нет линии — стоп
                self._state = RobotState.STOPPED
                self._robot.stop()
                self._pid.reset()
                self._last_seen_error = 0
            else:
                # search mode
                self._state = RobotState.SEARCHING
                cfg = self._cfg
                if self._last_seen_error > 0:
                    self._robot.send_pwm(cfg.search_fast, cfg.search_slow)
                elif self._last_seen_error < 0:
                    self._robot.send_pwm(cfg.search_slow, cfg.search_fast)
                else:
                    self._robot.stop()

    def run(self):
        while True:
            self.step()
            time.sleep(self._cfg.loop_interval)
