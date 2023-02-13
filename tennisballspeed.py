import torch
import cv2 as cv
from tello_asyncio import VIDEO_URL
from collections import deque
import time
from ball_speed_methods import average, calc_speed, pixels_to_speed, distance_finder, focal_length, measure_ball


"""Test Script to help troubleshoot model identification of faces and tennis balls.

This script provides a GUI that shows user the current measurements so that they can
be compared and contrasted with physical measurements. Tennis ball must be in frame 
for first pass of test script.
"""


import asyncio
from tello_asyncio import Tello, VIDEO_URL

# TODO: test w/ droe

# declare measuring values:
BALL_DIST = 30  # cm
BALL_WIDTH = 6.3  # cm
# Defining the fonts family, size, type
fonts = cv.FONT_HERSHEY_COMPLEX
# Definition of the RGB Colors format
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)

# initialize model and camera connection with drone
model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/runs/train/yolov7-AlTello6/weights/best.pt')

import objc

objc.loadBundle('CoreWLAN',
                bundle_path = '/System/Library/Frameworks/CoreWLAN.framework',
                module_globals = globals())

iface = CWInterface.interface()

networks, error = iface.scanForNetworksWithName_error_('TELLO-F235F8', None)

network = networks.anyObject()

success, error = iface.associateToNetwork_password_error_(network, '', None)
# async def main():
#     drone = Tello()
#     await drone.wifi_wait_for_network(prompt=True) # TELLO-F235F8
#
#     print('...ok, can connecting to drone now')
#     await drone.connect()
#
#     snr = await drone.wifi_signal_to_noise_ratio
#     print(f'WiFi signal to noise ratio: {snr}%')
#
#
# # Python 3.7+
# #asyncio.run(main())
# loop = asyncio.get_event_loop()
# loop.run_until_complete(main())

async def main():
    drone = Tello()
    await drone.wifi_wait_for_network(prompt=False)
    await drone.connect()
    await drone.takeoff()
    await drone.land()

# Python 3.7+
#asyncio.run(main())
loop = asyncio.get_event_loop()
loop.run_until_complete(main())

cap = cv.VideoCapture('udp://192.168.10.1:11111')
cap.open('udp://192.168.10.1:11111')
# cap = cv.VideoCapture(0)


print("Camera Ready. Ensure that there is only one tennis ball and no faces in the frame.")

ret, frame = cap.read()

focal_length_found = focal_length(BALL_DIST, BALL_WIDTH, measure_ball(frame, model, False)[0])
print(f"Camera focal length is {focal_length_found}")


last_dist = {'x': 0, 'y': 0, 'z': 0}
change_in_dist_z = 0

speeds_x = deque((0, 0, 0), maxlen=3)
speeds_y = deque((0, 0, 0), maxlen=3)
speeds_z = deque((0, 0, 0), maxlen=3)
avg_speed = {'x': 0, 'y': 0, 'z': 0}

ball_pixels = 0


# loop to assess the performance of speed calculator
while True:
    print("focal length found: ", focal_length_found)
    initial_time = time.time()
    _, frame = cap.read()

    # calling face_data function
    model_start_time = time.time()
    r = measure_ball(frame, model, False)

    if r is not None:
        ball_pixels = r[0]
        ball_location = r[1]
        model_ru = time.time() - model_start_time
        distance = distance_finder(focal_length_found, BALL_WIDTH, ball_pixels)

        # converting centimeters into meters
        dist_meters_z = distances
        change_in_dist_z = last_dist['z'] - dist_meters_z
        change_in_time = time.time() - initial_time
        # calculating the speed in of cords
        speeds_z.append(calc_speed(change_in_dist_z, change_in_time))

        speeds_x.append(pixels_to_speed('x', last_dist, ball_location, ball_pixels, change_in_time))
        speeds_y.append(-1 * pixels_to_speed('y', last_dist, ball_location, ball_pixels, change_in_time))

        # Care less about z directio
        avg_speed['z'] = abs(average(speeds_z))
        avg_speed['x'] = average(speeds_x)
        avg_speed['y'] = average(speeds_y)

        # graph speed vector
        cv.arrowedLine(frame, (ball_location['x'], ball_location['y']),
                       (2*ball_location['x'] - last_dist['x'], 2*ball_location['y'] - last_dist['y']), RED, 2)
        # log all measurements for next loop
        last_dist['z'] = dist_meters_z
        last_dist['x'] = ball_location['x']
        last_dist['y'] = ball_location['y']

    else:
        avg_speed['z'] = 0
        avg_speed['x'] = 0
        avg_speed['y'] = 0

    # code to display speeds and other measurements on frame variable
    speedFill = int(45 + (avg_speed['z']) * 130)
    if speedFill > 235:
        speedFill = 235
    # cv2.line(image, start_point, end_point, color, thickness)
    cv.line(frame, (45, 70), (235, 70), (0, 255, 0), 35)
    # speed dependent line
    cv.line(frame, (45, 70), (speedFill, 70), (255, 255, 0), 32)
    cv.line(frame, (45, 70), (235, 70), (0, 0, 0), 22)
    # print()
    cv.putText(frame, f"Z Speed: {round(avg_speed['z'], 2)} m/s", (50, 75), fonts, 0.6, (0, 255, 220), 2)

    # Writing Text on the displaying screen
    cv.line(frame, (45, 25), (255, 25), (255, 0, 255), 30)
    cv.line(frame, (45, 25), (255, 25), (0, 0, 0), 22)
    cv.putText(
        frame, f"Z Dist = {round(dist_meters_z, 2)} m", (50, 30), fonts, 0.6, WHITE, 2)

    cv.line(frame, (45, 115), (255, 115), (0, 255, 0), 30)
    cv.line(frame, (45, 115), (255, 115), (0, 0, 0), 22)
    cv.putText(
        frame, f"X Speed: {round(avg_speed['x'], 2)} m/s", (50, 120), fonts, 0.6, WHITE, 2)

    cv.line(frame, (45, 155), (255, 155), (0, 255, 0), 30)
    cv.line(frame, (45, 155), (255, 155), (0, 0, 0), 22)
    cv.putText(
        frame, f"Y Speed: {round(avg_speed['y'], 2)} m/s", (50, 160), fonts, 0.6, WHITE, 2)

    overall_time = time.time() - initial_time
    cv.line(frame, (45, 195), (255, 195), (0, 0, 255), 30)
    cv.line(frame, (45, 195), (255, 195), (0, 0, 0), 22)
    cv.putText(
        frame, f"FPS = {round(1 / overall_time, 2)} ", (50, 200), fonts, 0.6, WHITE, 2)

    cv.imshow("frame", frame)
    if cv.waitKey(1) == ord("q"):
        break

    print(f"Overal time is {overall_time}")
    print(f"model time is {model_ru}")

if cap:
    cap.release()
    cv.destroyAllWindows()
