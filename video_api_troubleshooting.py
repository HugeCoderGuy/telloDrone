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

# THIS SCRIPT HAS THE MOST PROMISE
class Controller():
    def __init__(self, drone, model):
        self.drone = drone
        self.stopped = False
        self.results = None
        self.model = model
        self.model_runners = 0
        self.delay_other_runners = False
        self.numb_runners = 8
        self.runner_going = 100*[None]
        self.counter = 0
        self.runner_id = 0

    def start(self):
        Thread(target=self.takeoff, args=()).start()
        return self

    def takeoff(self):
        self.drone.takeoff()
        time.sleep(5)

    def test_fast(self):
        self.drone.set_roll(-1)
        time.sleep(.5)
        self.drone.set_roll(0)
        time.sleep(5)

    def start_fast_mode(self):
        Thread(target=self.test_fast, args=()).start()
        return self

    def land(self):
        self.drone.land()
        time.sleep(5)

    def model_handler(self, frame, runner_id):
        self.model_runners += 1
        self.delay_other_runners = True
        self.runner_going[self.counter] = (runner_id, True)
        self.counter += 1
        time.sleep(.5)
        self.delay_other_runners = False
        self.results = measure_ball(frame, self.model, False)
        self.runner_going[self.counter] = (runner_id, False)
        self.counter += 1
        self.model_runners -= 1

    def run_model(self, frame):
        if self.model_runners <= self.numb_runners and self.delay_other_runners is False:
            if self.runner_id == self.numb_runners:
                self.runner_id = 0
            Thread(target=self.model_handler, args=(frame, self.runner_id)).start()
            self.runner_id += 1
        else:
            pass


    def stop(self):
        self.stopped = True
        Thread(target=self.land, args=()).start()
        return self

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
                # if counter == 150:
                #     controller.start()
                # if counter == 250:
                #     controller.start_fast_mode()
                # if counter == 400:
                #     controller.stop()
                cv2.waitKey(1)
                if frame.time_base < 1.0 / 60:
                    time_base = 1.0 / 60
                else:
                    time_base = frame.time_base
                frame_skip = int((time.time() - start_time) / time_base)
                counter += 1
                # print(counter)
                controller.run_model(image)
                print(controller.runner_going)
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