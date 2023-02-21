import sys
import traceback
import tellopy
import av
import cv2.cv2 as cv2  # for avoidance of pylint error
import numpy
import time
from threading import Thread

frame_qty = [i for i in range(0, 800, 50) if i % 50 == 0]

class VideoFeed():
    def __init__(self, container):
        self.frame = None
        self.stopped = False
        self.container = container
        
    def start(self):
        Thread(target=self.update_frame, args=()).start()
        return self
        
    def update_frame(self):
        for frame in self.container:
            self.frame = cv2.cvtColor(numpy.array(frame.to_image()), cv2.COLOR_RGB2BGR)
            
    def stop(self):
        self.stopped = True

            

def main():
    drone = tellopy.Tello()

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
                
        videofeed = VideoFeed(container)
        videofeed.start()

        move_dist = 15
        counter = 0

        while True:
            if counter == frame_qty[0]:
                drone.takeoff()
            elif counter == frame_qty[1]:
                drone.up(move_dist)
            elif counter == frame_qty[2]:
                drone.backward(move_dist)
            elif counter == frame_qty[3]:
                drone.toggle_fast_mode()
                time.sleep(1)
                drone.forward(move_dist)
            elif counter == frame_qty[4]:
                drone.land()
                time.sleep(2)
                videofeed.stop()
                break

            
            cv2.imshow('Original', videofeed.frame)
            counter += 1



    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        drone.quit()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()