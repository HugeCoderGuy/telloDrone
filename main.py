"""main.py manages the drone/video process and the model/decision process

Running the script requires you to load the model firs while
connected to wifi. Once the model has loaded, switch you wifi
network to the powered on Tello's wifi. 

Completion of the script occurs when the you press enter in the 
terminal. Drone will land and both processes will close out. 
"""

from ModelHandler import model_handler, test_func
# from TelloDriver import TelloDriver
from VideoHandler import video_handler
import torch
import sys
sys.path.insert(0, './yolov7')
import platform
# if platform.system() != "Linux":
#     from multiprocessing import set_start_method
#     set_start_method("fork")
import multiprocessing

# TODO include "yolov7/best.pt"
if __name__ == '__main__':
    # BaseManager.register("Tello", tellopy.Tello)
    # manager = BaseManager()
    # manager.start()
    # drone = manager.Tello()
    # drone.toggle_fast_mode()
    # model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')

    # # connect to drone to then create the video feed
    # drone = tellopy.Tello()
    # drone.connect()
    # drone.wait_for_connection(60.0)
    # item = drone.get_video_stream()


    # with multiprocessing.Manager() as manager:
        # Creating seperate pipes to link frames to model and model to drone
    parent_conn_frame, child_conn_frame = multiprocessing.Pipe()
    parent_conn_results, child_conn_results = multiprocessing.Pipe()
    
    state = multiprocessing.Value('i', 0)
    go = multiprocessing.Value('i', 0)
    stop = multiprocessing.Value('i', 0)

    # Create the three process that define the drone funciton
    frame_process = multiprocessing.Process(target=video_handler, args=(parent_conn_frame, state, go, stop))
    # model_process = multiprocessing.Process(target=model_handler, args=(model, child_conn_frame, state, go, stop))
    command_process = multiprocessing.Process(target=test_func, args=(state, go))

    # begin and end the processes!
    frame_process.start()
    # model_process.start()
    command_process.start()

    input("Press enter in the terminal to stop the drone")
    stop.value = 1
    frame_process.join()
    # model_process.join()
    command_process.join()