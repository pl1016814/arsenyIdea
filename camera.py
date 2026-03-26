import cv2, threading, time

#Camera Class

class CameraStream:
  def __init__(self, url):
    self._stream_url = url
    self._frame = None
    self._stopped = threading.lock()
    threading.Thread(target=self.update, daemon=True).start()

  def update(self):
    cap = cv2.VideoCapture(self._stream_url)
    while True:
      if not cap.isOpened():
        cap.release()
        time.sleep(2)
        cap = cv2.VideoCapture(self._stream_url)
        continue
      _, frame = cap.read()

      if frame is None:
        continue

      with self._stopped:
        self._frame = frame.copy()

  def get_frame(self):
    with self._stopped:
      if self_._frame is None:
        return None
      return self._frame.copy()
