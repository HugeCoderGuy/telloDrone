from multiprocessing.managers import BaseManager

from ModelHandler import model_handler
# from TelloDriver import TelloDriver
from VideoHandler import video_handler
import tellopy
import torch
import av
import sys
sys.path.insert(0, './yolov7')
import platform
if platform.system() != "Linux":
    from multiprocessing import set_start_method
    set_start_method("fork")
import multiprocessing


if __name__ == '__main__':
    # BaseManager.register("Tello", tellopy.Tello)
    # manager = BaseManager()
    # manager.start()
    # drone = manager.Tello()
    # drone.toggle_fast_mode()
    # model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')

    # # connect to drone to then create the video feed
    # drone.connect()
    # drone.wait_for_connection(60.0)
    drone = None



    # with multiprocessing.Manager() as manager:
        # Creating seperate pipes to link frames to model and model to drone
    parent_conn_frame, child_conn_frame = multiprocessing.Pipe()
    parent_conn_results, child_conn_results = multiprocessing.Pipe()

    # Create the three process that define the drone funciton
    frame_process = multiprocessing.Process(target=video_handler, args=(drone, parent_conn_frame))
    # model_process = multiprocessing.Process(target=model_handler(model, child_conn_frame, parent_conn_results))
    # command_process = multiprocessing.Process(target=TelloDriver.main, args=(drone, child_conn_results))

    # begin and end the processes!
    frame_process.start()
    # model_process.start()
    # command_process.start()

    frame_process.join()
    # model_process.join()
    # command_process.join()