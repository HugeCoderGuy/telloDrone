from collections import deque


BALL_WIDTH = 6.8  # cm


# takes frame and then returns any tennis ball locations
def measure_ball(frame, model):
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


# calculate speed in x from pixels to m/s
def pixels_to_speed(cord: str, last_dist: dict, ball_location: dict, ball_pixels: int, change_in_time: float):
    pixel_chg = ball_location[cord] - last_dist[cord]
    change_in_dist = pixel_chg * (BALL_WIDTH / ball_pixels)  # = pixel*(meters/pixels)
    # save x value after dist calc
    return calc_speed(change_in_dist, change_in_time)