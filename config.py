from dataclasses import dataclass

@dataclass
class Config:
  stream_url: str= "http://192.168.240.150:8080/video_feed"
  robot_url:  str= "http://192.168.240.150:8080"
  host_ip:    str= "0.0.0.0"
  port:       int= 8080

  #ROBOT
  base_speed: int   = 50
  left_motor:  float= 1.0
  right_motor: float= 0.35
  speed:       int   = 50
  search_fast: int   = 34
  search_slow: int   = 20

  #PD
  kp: float = 0.15
  kd: float = 0.45

  #DETECTION
  dead_zone: int = 10
  scan_rows: tuple = (0.5, 0.65, 0.8)
  lost_lines: int = 10 # frames before stop

  loop_time: float= 0.05
