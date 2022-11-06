import torch
import cv2 as cv
from tello_asyncio import VIDEO_URL
from collections import deque
import time

# TODO: make this script ru ad be able to measure speed

# declare measuring values:
BALL_DIST = 30 #cm
BALL_WIDTH = 6.8 #cm
#Defining the fonts family, size, type
fonts = cv.FONT_HERSHEY_COMPLEX
# Definition of the RGB Colors format
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)

# initialize model and camera connection with drone
model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt', cfg="cfg/deploy/yolov7-tiny.yaml")
# cap = cv.VideoCapture(VIDEO_URL)
# cap.open(VIDEO_URL)
cap = cv.VideoCapture(0)

print("Camera Ready. Ensure that there is only one tennisball and no faces in the frame.")

ret, frame = cap.read()


def measure_ball(frame):
    detections = model(frame[..., ::-1])
    result = detections.pandas().xyxy[0].to_dict(orient="records")
    if len(result) > 0:
        for i in result:
            if i["name"] == "Tennis-Ball" or "face":
                ball = i
                break
        measured_width = int(ball['xmax']) - int(ball['xmin'])
        measured_height = int(ball['ymax']) - int(ball['ymin'])
        # ball should be in square bound box. take average for ~ square dims
        ball_size = (measured_width + measured_height)/2
        ball_location = {'x': int(sum(ball['xmax'], ball['xmin']) / 2),
                         'y': int(sum(ball['ymax'], ball['ymin']) / 2)}
        return ball_size, ball_location


# Source: https://www.section.io/engineering-education/approximating-the-speed-of-an-object-and-its-distance/
def focal_length(determined_distance, actual_width, width_in_rf_image):
    focal_length_value = (width_in_rf_image * determined_distance) / actual_width
    return focal_length_value


def distance_finder(focal_length, real_ball_width, ball_width):
    if ball_width is not None:
        distance = (real_ball_width * focal_length) / ball_width
        return distance
    else:
        return 0


def average(items: deque):
    return sum(items) / len(items)


def calc_speed(dist: float, time: float) -> float:
    # requires dists to be in meters. time in seconds
    return dist / time



focal_length_found = focal_length(BALL_DIST, BALL_WIDTH, measure_ball(frame))
print(f"Camera focal length is {focal_length_found}")

# create collections.deque list with zeros
dists_x = deque([0, 0, 0], maxlen=3)
dists_y = deque([0, 0, 0], maxlen=3)
dists_z = deque([0, 0, 0], maxlen=3)

last_dist = {'x': 0, 'y': 0, 'z': 0}
change_in_dist = {'x': 0, 'y': 0, 'z': 0}

speeds_x = deque((0, 0, 0), maxlen=3)
speeds_y = deque((0, 0, 0), maxlen=3)
speeds_z = deque((0, 0, 0), maxlen=3)
avg_speed = {'x': 0, 'y': 0, 'z': 0}


initial_time = 0
change_in_time = time.time()
ball_pixels = 0

# TODO the average filter doesnt work because you find the chane between the last value and teha verage of several
# loop to assess the performance of speed calculator
while True:
    _, frame = cap.read()

    # calling face_data function
    loop_start_time = time.time()
    ball_pixels, ball_location = measure_ball(frame)
    model_ru = time.time() - loop_start_time

    if ball_pixels != 0:
        distance = distance_finder(focal_length_found, BALL_WIDTH, ball_pixels)
        dists_z.append(distance)
        average_distance = average(dists_z)

        # converting centimeters into meters
        dist_meters = average_distance / 100
        change_in_dist[2] = last_dist['z'] - dist_meters
        last_dist['z'] = dist_meters
        change_in_time = time.time() - initial_time

        # calculating the speed in z
        speed_z = calc_speed(change_in_dist[2], change_in_time)
        speeds_z.append(speed_z)
        avg_speed['z'] = abs(average(speeds_z))
        print((speed_z, speeds_z, avg_speed['z']))

        # calculate speed in x
        dists_x.ball_location

    else:
        avg_speed['z'] = 0
        avg_speed['x'] = 0
        avg_speed['y'] = 0

        # filling the progressive line dependent on the speed.
    speedFill = int(45 + (avg_speed['z']) * 130)
    if speedFill > 235:
        speedFill = 235
    cv.line(frame, (45, 70), (235, 70), (0, 255, 0), 35)
    # speed dependent line
    cv.line(frame, (45, 70), (speedFill, 70), (255, 255, 0), 32)
    cv.line(frame, (45, 70), (235, 70), (0, 0, 0), 22)
    # print()
    cv.putText(frame, f"Speed: {round(avg_speed, 2)} m/s", (50, 75), fonts, 0.6, (0, 255, 220), 2)

    # print(speed)
    initial_time = time.time()

    # Writing Text on the displaying screen
    cv.line(frame, (45, 25), (255, 25), (255, 0, 255), 30)
    cv.line(frame, (45, 25), (255, 25), (0, 0, 0), 22)
    cv.putText(
        frame, f"Distance = {round(dist_meters, 2)} m", (50, 30), fonts, 0.6, WHITE, 2)
    # recording the video
    # Recorder.write(frame)
    cv.imshow("frame", frame)
    if cv.waitKey(1) == ord("q"):
        break

    overall = time.time() - loop_start_time
    print(f"Overalt time is {overall}")
    print(f"model time is {model_ru}")