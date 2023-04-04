import time
from threading import Thread
from ball_speed_methods import measure_ball
import torch
import tellopy

# THIS SCRIPT HAS THE MOST PROMISE
class Controller():
    def __init__(self, drone):
        self.drone = drone
        self.stopped = False
        self.results = None
        self.model_runners = 0
        self.delay_other_runners = False
        self.numb_runners = 8
        self.debug = False

            
    def pause_after_call(self):
        time.sleep(4)

    def takeoff(self):
        def drone_takeoff(self):
            self.stopped = True
            self.drone.takeoff()
            self.pause_after_call()
            time.sleep(1)
        Thread(target=drone_takeoff, args=(self,)).start()
        return self

    #TODO try fliping the drone with roll set to max value
    
    def dodge_left(self):
        def drone_dodge_left(self):
            self.drone.set_roll(-1)
            time.sleep(.5)
            self.drone.set_roll(0)
            self.drone.flip_left()
            self.pause_after_call()

        Thread(target=drone_dodge_left, args=(self,)).start()
        return self
    

    def dodge_right(self):
        def drone_dodge_right(self):
            self.drone.set_roll(1)
            time.sleep(.5)
            self.drone.set_roll(0)
            self.pause_after_call()
            
        Thread(target=drone_dodge_right, args=(self,)).start()
        return self
    
    def dodge_up(self):
        def drone_jump(self):
            self.drone.set_throttle(1)
            time.sleep(.35)
            self.drone.set_throttle(-1)
            time.sleep(.25)
            self.drone.set_throttle(0)
            self.pause_after_call()
        
        Thread(target=drone_jump, args=(self,)).start()
        return self
    
    def go_forward(self):
        def drone_forward(self):
            self.drone.set_pitch(.4)
            time.sleep(.8)
            self.drone.set_pitch(0)
            self.pause_after_call()
            
        Thread(target=drone_forward, args=(self,)).start()
        return self
    
    def go_backward(self):
        def drone_backward(self):
            self.drone.set_pitch(-.4)
            time.sleep(.8)
            self.drone.set_pitch(0)
            self.pause_after_call()
            
        Thread(target=drone_backward, args=(self,)).start()
        return self
    
    def clockwise(self):
        def drone_clockwise(self):
            self.drone.set_yaw(.3)
            time.sleep(.8)
            self.drone.set_yaw(0)
            self.pause_after_call()
            
        Thread(target=drone_clockwise, args=(self,)).start()
        
    def counter_clockwise(self):
        def drone_counter_clockwise(self):
            self.drone.set_yaw(.3)
            time.sleep(.8)
            self.drone.set_yaw(0)
            self.pause_after_call()
            
        Thread(target=drone_counter_clockwise, args=(self,)).start()
        
    def up(self):
        def drone_up(self):
            self.drone.set_throttle(.5)
            time.sleep(.2)
            self.drone.set_throttle(0)
            self.pause_after_call()
            
        Thread(target=drone_up, args=(self,)).start()
        
    def down(self):
        def drone_down(self):
            self.drone.set_throttle(-.4)
            time.sleep(.3)
            self.drone.set_throttle(0)
            self.pause_after_call()
            
        Thread(target=drone_down, args=(self,)).start()
        
    def land(self):
        def drone_land(self):
            self.drone.land()
            self.pause_after_call()
            self.stopped = True
            
        Thread(target=drone_land, args=(self,)).start()
        return self

    def is_disconnected(self):
        print('the drone state is ', self.drone.state)
        return self.drone.state == State('disconnected')


class State(object):
    def __init__(self, name='annoymous'):
        self.name = name

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '%s::%s' % (self.__class__.__name__, self.name)

    def getname(self):
        return self.name

if __name__ == "__main__":
    drone = tellopy.Tello()
    drone.connect()
    drone.wait_for_connection(60.0)


    controller = Controller(drone)
    controller.start()
    controller.dodge_up()