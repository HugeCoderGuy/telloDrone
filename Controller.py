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
        self.debug = False
        
        if self.debug:
            # variables to used to confirm that model threads are processing in order
            self.runner_going = 100*[None]
            self.counter = 0
            self.runner_id = 0
            
    def pause_after_call(self):
        time.sleep(4)

    def start(self):
        Thread(target=self.takeoff, args=()).start()
        return self

    def takeoff(self):
        self.stopped = True
        self.drone.takeoff()
        self.pause_after_call()
        
        
    #TODO try fliping the drone with roll set to max value
    def dodge_left(self):
        self.drone.set_roll(-1)
        time.sleep(.5)
        self.drone.set_roll(0)
        self.pause_after_call()

    def thread_dodge_left(self):
        Thread(target=self.dodge_left, args=()).start()
        return self
    
    def dodge_right(self):
        self.drone.set_roll(-1)
        time.sleep(.5)
        self.drone.set_roll(0)
        self.pause_after_call()

    def thread_dodge_right(self):
        Thread(target=self.dodge_right, args=()).start()
        return self
    
    def dodge_up(self):
        def drone_jump(self):
            self.drone.set_throttle(1)
            time.sleep(.5)
            self.drone.set_throttle(-1)
            time.sleep(.5)
            self.drone.set_throttle(0)
            self.pause_after_call()
        
        Thread(target=drone_jump, args=()).start()
        return self
    
    def go_forward(self):
        def drone_forward(self):
            self.drone.forward(10)
            self.pause_after_call()
            
        Thread(target=self.drone_forward, args=()).start()
        return self
    
    def go_backward(self):
        def drone_backward(self):
            self.drone.backward(10)
            self.pause_after_call()
            
        Thread(target=self.drone_backward, args=()).start()
        return self
    
    def clockwise(self):
        def drone_clockwise(self):
            self.drone.clockwise(5)
            self.pause_after_call()
            
        Thread(target=drone_clockwise, args=()).start()
        
    def counter_clockwise(self):
        def drone_counter_clockwise(self):
            self.drone.counter_clockwise(5)
            self.pause_after_call()
            
        Thread(target=drone_counter_clockwise, args=()).start()

    def land(self):
        self.drone.land()
        self.pause_after_call()
        
    def stop(self):
        self.stopped = True
        Thread(target=self.land, args=()).start()
        return self

    # following two functs handle the object detection threads
    def model_handler(self, frame, runner_id):
        self.model_runners += 1
        self.delay_other_runners = True
        if self.debug:
            self.runner_going[self.counter] = (runner_id, True)
            self.counter += 1
        time.sleep(.5)
        self.delay_other_runners = False
        self.results = measure_ball(frame, self.model, False)
        if self.debug:
            self.runner_going[self.counter] = (runner_id, False)
            self.counter += 1
        self.model_runners -= 1

    def run_model(self, frame):
        if self.model_runners <= self.numb_runners and self.delay_other_runners is False:
            if self.debug:
                if self.runner_id == self.numb_runners:
                    self.runner_id = 0
                    
            Thread(target=self.model_handler, args=(frame, self.runner_id)).start()
            self.runner_id += 1
        else:
            pass


