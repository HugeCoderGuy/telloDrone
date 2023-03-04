import torch
import time
from threading import Thread
from ball_speed_methods import measure_ball

delay_other_runners = False
model_runners = 0
result = None


def model_handler(model, recv_conn, send_conn):
    global delay_other_runners
    global model_runners
    runner_delay = .3
    global result
    numb_runners = 8

    def _model_handler(frame):
        model_runners += 1
        delay_other_runners = True
        time.sleep(runner_delay)
        delay_other_runners = False
        result = measure_ball(frame, model, False)
        model_runners -= 1


    while True:
        print("we've made it to model script", flush=True)
        frame = recv_conn.recv()
        print("recieved a frame", flush=True)
        # method to skip processing frames if all model threads are currently working. delay is to force latency
        if model_runners <= numb_runners and delay_other_runners is False:
            Thread(target=_model_handler, args=(frame,)).start()
        else:
            pass
        if result is not None:
            print(result, flush=True)
            send_conn.send(result)
            result = None
    else:
        raise AttributeError("No Model instantiated to process frames with!")

def test_func(recv_pipe):
    while True:
        print(recv_pipe.recv())
        print("WE MADE IT", flush=True)
# TODO, This needs to be a function, not a class
class ModelHandler:
    def __init__(self, model, recv_conn, send_conn):
        self.model = model
        self.recv_conn = recv_conn
        self.send_conn = send_conn

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

    def model_handler(self, frame, runner_id=0):
        self.model_runners += 1
        self.delay_other_runners = True
        if self.debug:
            self.runner_going[self.counter] = (runner_id, True)
            self.counter += 1
        time.sleep(self.runner_delay)
        self.delay_other_runners = False
        result = measure_ball(frame, self.model, False)
        if self.debug:
            self.runner_going[self.counter] = (runner_id, False)
            self.counter += 1
        self.model_runners -= 1
        self.send_conn.send(result)

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
        