import cv2
import time
import numpy
import sys
import traceback
import av
import tellopy
import numpy as np
from threading import Thread
# import imutils

def video_handler(drone, send_conn):
    print("VIDEO HANDLER", flush=True)
    drone = tellopy.Tello()
    # drone.toggle_fast_mode()
    # # model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')
    #
    # # # connect to drone to then create the video feed
    drone.connect()
    drone.wait_for_connection(60.0)
    try:
        retry = 3
        container = None
        while container is None and 0 < retry:
            retry -= 1
            try:
                container = av.open(drone)
            except av.AVError as ave:
                print(ave, flush=True)
                print('retry...', flush=True)
        # skip first 300 frames
        frame_skip = 300
        while True:
            for frame in container.decode(video=0):
                if 0 < frame_skip:
                    frame_skip = frame_skip - 1
                    continue
                start_time = time.time()
                # image = np.array(frame.to_image())
                # image = imutils.resize(image, width=400)
                image = cv2.cvtColor(numpy.array(frame.to_image()), cv2.COLOR_RGB2BGR)
                cv2.imshow('Tello View', image)
                cv2.waitKey(1)
                # transfer frame to model pipeline
                send_conn.send(image)
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

# def get_frame_read(self) -> 'BackgroundFrameRead':
#     """Get the BackgroundFrameRead object from the camera drone. Then, you just need to call
#     backgroundFrameRead.frame to get the actual frame received by the drone.
#     Returns:
#         BackgroundFrameRead
#     """
#     if self.background_frame_read is None:
#         address = self.get_udp_video_address()
#         self.background_frame_read = BackgroundFrameRead(self, address)
#         self.background_frame_read.start()
#     return self.background_frame_read

class BackgroundFrameRead:
    """
    This class read frames using PyAV in background. Use
    backgroundFrameRead.frame to get the current frame.
    """

    def __init__(self):
        drone = tellopy.Tello()
        drone.connect()
        drone.wait_for_connection(60.0)
        self.frame = np.zeros([300, 400, 3], dtype=np.uint8)

        # Try grabbing frame with PyAV
        # According to issue #90 the decoder might need some time
        # https://github.com/damiafuentes/DJITelloPy/issues/90#issuecomment-855458905
        try:
            retry = 3
            container = None
            while container is None and 0 < retry:
                retry -= 1
                try:
                    self.container = av.open(drone.get_video_stream())
                except av.AVError as ave:
                    print(ave, flush=True)
                    print('retry...', flush=True)
        except Exception as ex:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            print(ex)

        self.stopped = False
        self.worker = Thread(target=self.update_frame, args=(), daemon=True)

    def start(self):
        """Start the frame update worker
        Internal method, you normally wouldn't call this yourself.
        """
        self.worker.start()

    def update_frame(self):
        """Thread worker function to retrieve frames using PyAV
        Internal method, you normally wouldn't call this yourself.
        """
        try:
            for frame in self.container.decode(video=0):
                self.frame = np.array(frame.to_image())
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