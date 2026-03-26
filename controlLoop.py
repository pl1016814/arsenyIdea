"""Controll loop"""

import time, threading
from config import Config
from dataclasses import dataclass

@dataclass
class State:
  STOPPED = "stopped"
  RUNNING = "running"
  SEARCHING = "searching"

class Controlling_loop:
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

  def status(self):
    return self._state
