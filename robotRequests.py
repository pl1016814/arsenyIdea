"""Robot_requests"""

import requests

class RobotRequests:
  def __init__(self, api_url, timeout = 1):
    self._url = api_url
    self._timeout = timeout
  def send_pwm(self, left,  right):
    try:
      requests.post(
          f"{self._url}/move_pwm"
          json={"left": left, "right": right},
          timeout=self._timeout
      )
    except Exeption as oshibka:
      print(f"Mr. Stern, Problem with robot api!!!")

  def stop(self):
    try:
      requests.post(
          f"{self._url}"/move/stop,
          timeout=self._timeout
      )
    except Exeption as oshibka:
      print(f"Mr. Stern, Problem with stopping api!!!")
