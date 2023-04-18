import torch
import time
from threading import Thread
from ball_speed_methods import measure_ball
from DroneEnum import DroneEnum
from queue import Queue
from TelloDriver import TelloDriver
import multiprocessing
import cv2


def model_handler(model, recv_conn: multiprocessing.Pipe, 
                  drone_state: multiprocessing.Queue, go: multiprocessing.Value,
                  stop: multiprocessing.Value):
    """Multiprocess.process handling the YoloV7 model
    
    Handler takes frames from video/drone process, passes them
    through the model and then processes the results. The drone
    commands are shared through drone_state.value to the other
    process that then drives the tello api

    Args:
        model (torch.model): Yolov7 model trained for balls & faces
        recv_conn (multiprocessing.Pipe): Drone/Video process
        drone_state (multiprocessing.Value): drone state that drives aciton
        go (multiprocessing.Value): a synchronizing int to prevent early instantiation
    """
    
    # delay instantiation of models and processing
    while go.value != 1:
        time.sleep(.5)
        
    frame = recv_conn.recv()
    tellodriver = TelloDriver(frame)
    modelhandler = ModelHandler(model, recv_conn, frame)

    try:
        while stop.value != 1:
            modelhandler.run_model()
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
                        drone_state.put(command_to_send)
                
    finally:
        modelhandler.end()


class ModelHandler:
    def __init__(self, model, recv_conn: multiprocessing.Pipe, frame):
        """Class to encapsulate the model threads
        
        Handles the models running in the background with synchronized
        threads adding their results to a queue. The queue is then 
        processed in by the TelloDriver class to identify action

        Args:
            model (torch.model): Yolov7 Model
            recv_conn (multiprocessing.Pipe): connection to drone/video process
        """
        self.model = model
        self.recv_conn = recv_conn
        self.result = Queue(maxsize=10)

        self.current_result = None  # used for display bounding boxes on video
        self.show_bb_for_frames = 5

        self.stopped = False
        self.model_runners = 0
        self.delay_other_runners = False
        self.runner_delay = .5
        self.numb_runners = 10

        self.debug = False
        if self.debug:
            # variables to used to confirm that model threads are processing in order
            self.runner_going = 100*[None]
            self.counter = 0
            self.runner_id = 0
            
        # video saving object for run_model
        # fourcc = cv2.VideoWriter_fourcc(*'XVID')
        fourcc = cv2.VideoWriter_fourcc(*'AVC1')
        self._out = cv2.VideoWriter('tello_video.avi', fourcc, 30, (960, 720)) # (640,480))
            
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

    def run_model(self):
        frame = self.recv_conn.recv()
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

        # print('CURRENT RESULT IS', self.current_result)
        # if self.current_result != None:
        #     print('1')
        #     for result in self.current_result:
        #         if result['name'] == 'Tennis-Ball':
        #             bb_color = (255, 0, 0)  # BGR
        #         elif result['name'] == 'face':
        #             bb_color = (0, 0, 255)  # BGR
        #         print('2')
        #         frame = cv2.rectangle(frame, (result['xmin'], result['ymin']), (result['xmax'], result['ymax']), bb_color, 2)
        #         print('3')
        self._out.write(frame)
        
    def end(self):
        self._out.release()
        

def test_func(state, go):
    """Periodically sends commands to Drone process to confirm that it works

    Args:
        state (_type_): Drone State
        go (_type_): flag from drone process on when to start running models
    """
    while go.value != 1:
        time.sleep(.1)
    time.sleep(5)
    for drone_state in DroneEnum:
        print(f"STATE IS: {drone_state.name} !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", flush=True)
        state.value = drone_state.value
        time.sleep(6)

