import sys
import traceback
import tellopy
import av
import cv2.cv2 as cv2  # for avoidance of pylint error
import numpy
import time
from threading import Thread
from ball_speed_methods import measure_ball
import torch
from Controller import Controller


def main():
    drone = tellopy.Tello()
    drone.toggle_fast_mode()
    model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')
    controller = Controller(drone, model)
    try:
        drone.connect()
        drone.wait_for_connection(60.0)

        retry = 3
        container = None
        while container is None and 0 < retry:
            retry -= 1
            try:
                container = av.open(drone.get_video_stream())
            except av.AVError as ave:
                print(ave)
                print('retry...')

        # skip first 300 frames
        frame_skip = 300
        counter = 0
        while True:
            for frame in container.decode(video=0):
                if 0 < frame_skip:
                    frame_skip = frame_skip - 1
                    continue
                start_time = time.time()
                image = cv2.cvtColor(numpy.array(frame.to_image()), cv2.COLOR_RGB2BGR)
                cv2.imshow('Original', image)
                # cv2.imshow('Canny', cv2.Canny(image, 100, 200))
                if counter == 50:
                    print("ONONEONEOENO")
                    controller.start()
                if counter == 125:
                    print("TWPTWOTOWTWOWOT")
                    controller.counter_clockwise()
                if counter == 200:
                    print("THREEHTHRETHERE")
                    controller.clockwise()
                if counter == 275:
                    print("FOURFOURFOURFOUR")
                    controller.dodge_up()
                if counter == 350:
                    controller.stop()
                cv2.waitKey(1)
                if frame.time_base < 1.0 / 60:
                    time_base = 1.0 / 60
                else:
                    time_base = frame.time_base
                frame_skip = int((time.time() - start_time) / time_base)
                counter += 1
                print(counter)
                controller.run_model(image)
                # print(controller.results)



    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        drone.quit()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()