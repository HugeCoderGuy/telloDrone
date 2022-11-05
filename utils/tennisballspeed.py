import torch
import cv2
from tello_asyncio import VIDEO_URL
from collections import deque
import time

# declare measuring values:
BALL_DIST = 30 #cm
BALL_WIDTH = 6.8 #cm
#Defining the fonts family, size, type
fonts = cv2.FONT_HERSHEY_COMPLEX

# initialize model and camera connection with drone
model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')
cap = cv2.VideoCapture(VIDEO_URL)
cap.open(VIDEO_URL)

print("Camera Ready. Ensure that there is only one tennisball and no faces in the frame.")

ret, frame = cap.read()

def measure_ball(frame):
    detections = model(frame[..., ::-1])
    result = detections.pandas().xyxy[0].to_dict(orient="records")
    measured_width = int(result['xmax']) - int(result['xmin'])
    measured_height = int(result['ymax']) - int(result['ymin'])
    # ball should be in square bound box. take average for ~ square dims
    return (measured_width + measured_height)/2

# Source: https://www.section.io/engineering-education/approximating-the-speed-of-an-object-and-its-distance/
def focal_length(determined_distance, actual_width, width_in_rf_image):
    focal_length_value = (width_in_rf_image * determined_distance) / actual_width
    return focal_length_value

def distance_finder(focal_length, real_ball_width, face_width_in_frame):
    distance = (real_ball_width * focal_length) / face_width_in_frame
    return distance

focal_length_found = focal_length(BALL_DIST, BALL_WIDTH, measure_ball(frame))
print(f"Camera focal length is {focal_length_found}")

# create collections.deque list with zeros
dists = deque(maxlen=3)
for _ in range(3):
    dists.append(0)
speeds = deque(5)
for _ in range(5):
    dists.append(0)
initial_time = 0
initial_dist = 0
change_in_time = time.time()
change_in_dist = 0
ball_pixels = 0

# loop to assess the performance of speed calculator
while True:
    _, frame = cap.read()

    # calling face_data function
    ball_pixels = measure_ball(frame)
    # finding the distance by calling function Distance
    if ball_pixels != 0:
        distance = distance_finder(focal_length_found, BALL_WIDTH, ball_pixels)
        dists.append(distance)
        averagedistance = sum(dists) / len(dists)

        # converting centimeters into meters
        dist_meters = averagedistance / 100

    if initial_dist != 0:
        # getting the  difference of the distances
        change_in_dist = initial_dist - dist_meters
        change_in_time = time.time() - initial_time

    # calculating the speed
    speed = change_in_dist / change_in_time
    speeds.append(speed)
    averageSpeed = sum(speeds) / len(dists)
    if averageSpeed < 0:
        averageSpeed = averageSpeed * -1
        # filling the progressive line dependent on the speed.
    speedFill = int(45 + (averageSpeed) * 130)
    if speedFill > 235:
        speedFill = 235
    cv2.line(frame, (45, 70), (235, 70), (0, 255, 0), 35)
    # speed dependent line
    cv2.line(frame, (45, 70), (speedFill, 70), (255, 255, 0), 32)
    cv2.line(frame, (45, 70), (235, 70), (0, 0, 0), 22)
    # print()
    cv2.putText(frame, f"Speed: {round(averageSpeed, 2)} m/s", (50, 75), fonts, 0.6, (0, 255, 220), 2)

    # print(speed)
    initial_time = time.time()

    # Writing Text on the displaying screen
    cv2.line(frame, (45, 25), (255, 25), (255, 0, 255), 30)
    cv2.line(frame, (45, 25), (255, 25), (0, 0, 0), 22)
    cv2.putText(
        frame, f"Distance = {round(distanceInMeters, 2)} m", (50, 30), fonts, 0.6, WHITE, 2)
    # recording the video
    # Recorder.write(frame)
    cv2.imshow("frame", frame)
    if cv2.waitKey(1) == ord("q"):
        break