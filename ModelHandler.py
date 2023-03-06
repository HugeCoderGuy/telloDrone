import torch
import time
from threading import Thread
from ball_speed_methods import measure_ball
from DroneEnum import DroneEnum
from queue import Queue
from TelloDriver import TelloDriver



def model_handler(model, recv_conn, drone_state):
    modelhandler = ModelHandler(model, recv_conn)
    frame = recv_conn.recv()
    tellodriver = TelloDriver(frame)

    while True:
        modelhandler.run_model()
        if modelhandler.is_empty():
            pass
        else:
            result = modelhandler.get_result()
            tellodriver.update_object_variables(result)
            dodge_cmd = tellodriver.dodge_ball()
            if dodge_cmd:
                drone_state.value = dodge_cmd
                # make sure nothing interrupts the dodge call!
                time.sleep(5)
            
            drone_state.value = tellodriver.follow_face()

            

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
# TODO, This needs to be a function, not a class


class ModelHandler:
    def __init__(self, model, recv_conn):
        self.model = model
        self.recv_conn = recv_conn
        self.result = Queue(maxsize = 10)

        self.stopped = False
        self.model_runners = 0
        self.delay_other_runners = False
        self.runner_delay = .3
        self.numb_runners = 8

        self.debug = False
        if self.debug:
            # variables to used to confirm that model threads are processing in order
            self.runner_going = 100*[None]
            self.counter = 0
            self.runner_id = 0
            
    def get_result(self):
        return self.result.get()
    
    def is_empty(self):
        return self.result.empty()

    def model_handler(self, frame, runner_id=0):
        self.model_runners += 1
        self.delay_other_runners = True
        if self.debug:
            self.runner_going[self.counter] = (runner_id, True)
            self.counter += 1
        time.sleep(self.runner_delay)
        self.delay_other_runners = False
        detections = self.model(frame[..., ::-1])
        result = detections.pandas().xyxy[0].to_dict(orient="records")
        self.result.put(result)
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
                    if self.runner_id == self.numb_runners:
                        self.runner_id = 0

                    Thread(target=self.model_handler, args=(frame, self.runner_id)).start()
                    self.runner_id += 1

                # not debug mode:
                else:
                    Thread(target=self.model_handler, args=(frame,)).start()
            else:
                pass
        else:
            raise AttributeError("No Model instantiated to process frames with!")
        