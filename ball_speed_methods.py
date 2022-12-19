from collections import deque
import cv2 as cv
import math

BALL_WIDTH = 6.3  # cm


# takes frame and then returns any tennis ball locations
def measure_ball(frame, model, bound_box=True):
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
        x = int((ball['xmax'] + ball['xmin']) / 2)
        y = int((ball['ymax'] + ball['ymin']) / 2)
        ball_location = {'x': x, 'y': y}

        if not bound_box:
            return [ball_size, ball_location]
        else:
            cv.rectangle(frame, (ball['xmin'], ball['ymax']), (ball['xmax'], ball['ymax']),
                          (255, 0, 0), 4)
            return [ball_size, ball_location, frame]


# Source: https://www.section.io/engineering-education/approximating-the-speed-of-an-object-and-its-distance/
def focal_length(determined_distance, actual_width, width_in_rf_image):
    print(width_in_rf_image, type(width_in_rf_image))
    focal_length_value = (width_in_rf_image * determined_distance) / actual_width
    return focal_length_value


def distance_finder(focal_length, real_ball_width, ball_width):
    if ball_width is not None:
        distance = (real_ball_width * focal_length) / ball_width
        return distance / 100  # convert to meters
    else:
        return 0


def average(items: deque):
    return sum(items) / len(items)


def calc_speed(dist: float, time: float) -> float:
    # requires dists to be in meters. time in seconds
    return dist / time


# calculate speed in x from pixels to m/s
def pixels_to_speed(cord: str, last_dist: dict, ball_location: dict, ball_pixels: int, change_in_time: float):
    pixel_chg = ball_location[cord] - last_dist[cord]
    change_in_dist = pixel_chg * ((BALL_WIDTH * .01) / ball_pixels)  # = pixel*(meters/pixels)
    # save x value after dist calc
    return calc_speed(change_in_dist, change_in_time)


def distance_from_between_points(point1: dict, point2: dict) -> float:
    dist = math.sqrt( (point1['x'] - point2['x']) ** 2 +
                      (point1['y'] - point2['y']) ** 2)
    return dist