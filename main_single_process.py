import torch
import cv2
import time
import numpy
import sys
import traceback
import av
import tellopy
import numpy as np
from threading import Thread
from Controller import Controller
import queue
from DroneEnum import DroneEnum
from TelloDriver import TelloDriver
from VideoHandler import BackgroundFrameRead
import socket


class ModelHandler_alt:
    def __init__(self, model):
        """Class to encapsulate the model threads

        Handles the models running in the background with synchronized
        threads adding their results to a queue. The queue is then
        processed in by the TelloDriver class to identify action

        Args:
            model (torch.model): Yolov7 Model
            recv_conn (multiprocessing.Pipe): connection to drone/video process
        """
        self.model = model
        self.result = queue.Queue()

        self.current_result = None  # used for display bounding boxes on video
        self.show_bb_for_frames = 5

        self.stopped = False
        self.model_runners = 0
        self.delay_other_runners = False
        self.runner_delay =.5
        self.numb_runners = 10

        self.debug = False
        if self.debug:
            # variables to used to confirm that model threads are processing in order
            self.runner_going = 100 * [None]
            self.counter = 0
            self.runner_id = 0

        # video saving object for run_model
        # fourcc = cv2.VideoWriter_fourcc(*'XVID')
        fourcc = cv2.VideoWriter_fourcc(*'AVC1')
        self._out = cv2.VideoWriter('tello_video.avi', fourcc, 30, (960, 720))  # (640,480))

    def get_result(self):
        if not self.result.empty():
            return self.result.get()
        else:
            return False

    def is_empty(self):
        return self.result.empty()

    def toggle_runner_delay(self, delay):
        self.delay_other_runners = True
        time.sleep(delay)
        self.delay_other_runners = False

    def model_handler(self, frame, runner_id=0):
        self.model_runners += 1
        if self.debug:
            self.runner_going[self.counter] = (runner_id, True)
            self.counter += 1
        self.delay_other_runners = True
        detections = self.model(frame[..., ::-1])
        self.delay_other_runners = False
        result = detections.pandas().xyxy[0].to_dict(orient="records")
        if result != []:
            if self.debug:
                result[0]['runner_id'] = runner_id
            self.result.put(result)
            self.current_result = result
        if self.debug:
            self.runner_going[self.counter] = (runner_id, False)
            self.counter += 1
        self.model_runners -= 1

    def run_model(self, frame):
        frame = frame
        if self.model:
            # method to skip processing frames if all model threads are currently working. delay is to force latency
            if self.model_runners <= self.numb_runners and self.delay_other_runners is False:
                if self.debug:
                    # if self.runner_id == self.numb_runners:
                    #     self.runner_id = 0

                    Thread(target=self.model_handler, args=(frame, self.runner_id,)).start()
                    Thread(target=self.toggle_runner_delay, args=(self.runner_delay,)).start()
                    print('DEBUGGING', self.runner_going, self.counter, flush=True)
                    self.runner_id += 1

                # not debug mode:
                else:
                    print('frame size is: ', frame.shape[:2], flush=True)
                    Thread(target=self.model_handler, args=(frame,)).start()
                    # Thread(target=self.toggle_runner_delay, args=(self.runner_delay,)).start()
            else:
                pass
        else:
            raise AttributeError("No Model instantiated to process frames with!")

        if self.current_result != None:
            for result in self.current_result:
                if result['name'] == 'Tennis-Ball':
                    bb_color = (255, 0, 0)  # BGR
                elif result['name'] == 'face':
                    bb_color = (0, 0, 255)  # BGR
                frame = cv2.rectangle(frame, (int(result['xmin']), int(result['ymin'])), (int(result['xmax']), int(result['ymax'])),
                                      bb_color, 2)

        # 720 by 960
        # clockwise ad cc
        cv2.line(frame, (int(960/2-150), 0), (int(960/2-150), 720), (0, 255, 255), 1)
        cv2.line(frame, (int(960/2 + 150), 0), (int(960/2 + 150), 720), (0, 255, 255), 1)
        # cv2.line(frame, (0, 960 - 125), (720, 960 - 120), (0, 255, 255), 1)
        # cv2.line(frame, (0, 960 + 125), (720, 960 + 120), (0, 255, 255), 1)

        cv2.line(frame, (0, int(720/2-200)), (960, int(720/2-200)), (0, 255, 0), 1)
        cv2.line(frame, (0, int(720/2 + 25)), (960, int(720/2 + 25)), (0, 255, 0), 1)
        self._out.write(frame)

    def end(self):
        self._out.release()

webcam = False

model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')

if not webcam:
    drone = tellopy.Tello()
    drone.connect()
    drone.wait_for_connection(60.0)
    # drone.toggle_fast_mode()
    # drone.set_att_limit(10)
    print('connected to drone', flush=True)

    retry = 3
    container = None
    while container is None and 0 < retry:
        retry -= 1
        try:
            container = av.open(drone.get_video_stream())
        except av.AVError as ave:
            print(ave, flush=True)
            print('retry...', flush=True)


# controller = Controller(drone)
# controller.takeoff()
# time.sleep(.5)


if webcam:
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()

else:
    backgroundframe = BackgroundFrameRead(container)
    backgroundframe.start()
    frame = backgroundframe.frame

state = queue.Queue()

tellodriver = TelloDriver(frame)

modelhandler = ModelHandler_alt(model)
stop = 0

try:
    while stop != 1:
        if webcam:
            ret, frame = cap.read()
        else:
            frame = backgroundframe.frame
        modelhandler.run_model(frame)
        if modelhandler.is_empty():
            pass
        else:
            result = modelhandler.get_result()
            if result:
                print(result, flush=True)
                tellodriver.update_object_variables(result)
                # dodge_cmd = tellodriver.dodge_ball()
                # # dodge command is processed first
                # if dodge_cmd:
                #     drone_state.put(dodge_cmd)
                #     # make sure nothing interrupts the dodge call!
                #     time.sleep(5)
                # if no dodge, allow drone to follow the face
                command_to_send = tellodriver.follow_face()
                if command_to_send != 0:
                    state.put(command_to_send)

        if not state.empty():
            print('here1', flush=True)

            curr_state = state.get()
            print(curr_state, flush=True)
            match curr_state:
                case DroneEnum.dodge_left.value:
                    print('Dodge Left', flush=True)
                case DroneEnum.dodge_right.value:
                    print('Dodge Right', flush=True)
                case DroneEnum.dodge_up.value:
                    print('Dodge Up', flush=True)
                case DroneEnum.forward.value:
                    print('Forward', flush=True)
                case DroneEnum.backward.value:
                    print('Backward', flush=True)
                case DroneEnum.clockwise.value:
                    print('Clockwise', flush=True)
                case DroneEnum.counter_clockwise.value:
                    print('Counter_Clockwise', flush=True)
                case DroneEnum.up.value:
                    print('Up', flush=True)
                case DroneEnum.down.value:
                    print('Down', flush=True)
                # if no commands, state = 0 and wildcard catches with pass
                case _:
                    pass

        cv2.imshow('frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('x'):
            break

finally:
    modelhandler.end()



