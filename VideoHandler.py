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
from DroneEnum import DroneEnum
import multiprocessing

# https://github.com/darkskyapp/forecast-ruby/issues/13 <---- threading issue needs to be documented


def video_handler(send_conn: multiprocessing.Pipe, state: multiprocessing.Value, 
                  go: multiprocessing.Value, stop: multiprocessing.Value):
    """Video/Drone process handling video feed and tello api calls
    
    Tello commands are filtered through wrapper class Controller.
    The video feed runs in the background as a thread to ensure that
    the frames don't lag.

    Args:
        send_conn (multiprocessing.Pipe): Pipe to model process sending frames
        state (multiprocessing.Value): current drone state shared as an int
        go (multiprocessing.Value): A flag shared between process to synchronize
        stop (multiprocessing.Value): indicator to end the process
    """
    drone = tellopy.Tello()
    drone.connect()
    drone.wait_for_connection(60.0)
    # drone.toggle_fast_mode()
    # drone.set_att_limit(10)
    print('connected to drone', flush=True)

    try:
        retry = 3
        container = None
        while container is None and 0 < retry:
            retry -= 1
            try:
                container = av.open(drone.get_video_stream())
            except av.AVError as ave:
                print(ave, flush=True)
                print('retry...', flush=True)


        controller = Controller(drone)
        controller.takeoff()
        time.sleep(.5)
        backgroundframe = BackgroundFrameRead(container)
        backgroundframe.start()
        time.sleep(2)

        # allow model process to begin
        go.value = 1
        while stop.value != 1:
            send_conn.send(backgroundframe.frame)
            # print('here1', flush=True)
            # print('here2', flush=True)
            # cv2.imshow('Tello View', backgroundframe.frame)
            # print('here3', flush=True)
            # cv2.waitKey(1)
            # process is to iterate through state value, act on it, then reset state
            if not state.empty():
                curr_state = state.get()
                print(curr_state, flush=True)
                match curr_state:
                    case DroneEnum.dodge_left.value:
                        controller.dodge_left()
                    case DroneEnum.dodge_right.value:
                        controller.dodge_right()
                    case DroneEnum.dodge_up.value:
                        controller.dodge_up()
                    case DroneEnum.forward.value:
                        controller.go_forward()
                    case DroneEnum.backward.value:
                        controller.go_backward()
                    case DroneEnum.clockwise.value:
                        controller.clockwise()
                    case DroneEnum.counter_clockwise.value:
                        controller.counter_clockwise()
                    case DroneEnum.up.value:
                        controller.up()
                    case DroneEnum.down.value:
                        controller.down()
                    # if no commands, state = 0 and wildcard catches with pass
                    case _:
                        pass
            if not controller.is_connected():
                stop.value = 1
                print('ENDING VIDEO HANDLER PROCESS', flush=True)
                    
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
            
    finally:
        # in event that drone is turned off, stop all other processes
        stop.value = 1
        backgroundframe.stop()
        controller.land()
        cv2.destroyAllWindows()
        # add a sleep command to ensure drone finishes landing
        time.sleep(3)


class BackgroundFrameRead:
    """
    This class read frames using PyAV in background. Use
    backgroundFrameRead.frame to get the current frame.
    """

    def __init__(self, container):
        self.frame = np.zeros([720, 960, 3], dtype=np.uint8)
        self.container = container

        self.stopped = False
        self.worker = Thread(target=self.update_frame, args=(), daemon=True)
        
    def start(self):
        self.worker.start()

    def update_frame(self):
        """Thread worker function to retrieve frames using PyAV
        Internal method, you normally wouldn't call this yourself.
        """
        frame_skip = 300
        try:
            for frame in self.container.decode(video=0):
                # self.frame = np.array(frame.to_image())
                if 0 < frame_skip:
                    frame_skip = frame_skip - 1
                    continue
                start_time = time.time()
                self.frame = cv2.cvtColor(numpy.array(frame.to_image()), cv2.COLOR_RGB2BGR)
                # cv2.imshow('Canny', cv2.Canny(image, 100, 200))
                if frame.time_base < 1.0 / 60:
                    time_base = 1.0 / 60
                else:
                    time_base = frame.time_base
                frame_skip = int((time.time() - start_time) / time_base)
                if self.stopped:
                    self.container.close()
                    break
        except av.error.ExitError as ave:
            print(ave, flush=True)
            print('retry...', flush=True)

    def stop(self):
        """Stop the frame update worker
        Internal method, you normally wouldn't call this yourself.
        """
        self.stopped = True

if __name__ == "__main__":
    frame_reader = BackgroundFrameRead()
    while True:
        try:
            # print(type(frame_reader.frame))
            cv2.imshow('tello', frame_reader.frame)
            cv2.waitKey()

        finally:
            cv2.destroyAllWindows()