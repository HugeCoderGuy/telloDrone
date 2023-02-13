import sys
import traceback
import tellopy
import av
import cv2.cv2 as cv2  # for avoidance of pylint error
import numpy
import time

frame_qty = [i for i in range(0, 800, 50) if i % 50 == 0]

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

        # skip first 300 frames
        frame_skip = 100
        alt_cmd = 0 # variable to flag alternating comands
        while True:
            for frame in container.decode(video=0):
                if 0 < frame_skip:
                    frame_skip = frame_skip - 1
                    if frame_skip == 50:
                        drone.takeoff()
                    continue
                else:
                    move_dist = 10
                    if alt_cmd == frame_qty[0]:
                        drone.up(move_dist)
                    if alt_cmd == frame_qty[1]:
                        drone.down(move_dist)
                    if alt_cmd == frame_qty[2]:
                        drone.forward(move_dist)
                    if alt_cmd == frame_qty[3]:
                        drone.clockwise(move_dist)
                    if alt_cmd == frame_qty[4]:
                        drone.counter_clockwise(move_dist)

                    if alt_cmd == frame_qty[5]:
                        print("testing overlap api calls!")
                        drone.left(20)
                        time.sleep(1)
                        print("switching from left to right")
                        drone.right(20)
                        time.sleep(.25)
                        drone.up(0)
                        print("FLIP!")
                        drone.flip_back()
                    if alt_cmd == frame_qty[6]:
                        drone.land()
                    alt_cmd += 1

                    start_time = time.time()
                    image = cv2.cvtColor(numpy.array(frame.to_image()), cv2.COLOR_RGB2BGR)
                    cv2.imshow('Original', image)
                    # cv2.imshow('Canny', cv2.Canny(image, 100, 200))
                    cv2.waitKey(1)
                    if frame.time_base < 1.0/60:
                        time_base = 1.0/60
                    else:
                        time_base = frame.time_base
                    frame_skip = int((time.time() - start_time)/time_base)


    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        drone.quit()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()