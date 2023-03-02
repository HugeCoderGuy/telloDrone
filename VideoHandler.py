import cv2
import time
import numpy
import sys
import traceback
import av
import tellopy

def video_handler(drone, send_conn):
    print("VIDEO HANDLER", flush=True)
    drone = tellopy.Tello()
    # drone.toggle_fast_mode()
    # model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')

    # # connect to drone to then create the video feed
    drone.connect()
    drone.wait_for_connection(60.0)
    try:
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
        while True:
            for frame in container.decode(video=0):
                if 0 < frame_skip:
                    frame_skip = frame_skip - 1
                    continue
                start_time = time.time()
                image = cv2.cvtColor(numpy.array(frame.to_image()), cv2.COLOR_RGB2BGR)
                cv2.imshow('Tello View', image)

                # transfer frame to model pipeline
                # send_conn.send(frame)
                # cv2.imshow('Canny', cv2.Canny(image, 100, 200))
                if frame.time_base < 1.0 / 60:
                    time_base = 1.0 / 60
                else:
                    time_base = frame.time_base
                frame_skip = int((time.time() - start_time) / time_base)


    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        cv2.destroyAllWindows()