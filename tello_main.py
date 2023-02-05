import torch
import cv2
import asyncio
from tello_asyncio import Tello, VIDEO_URL, Vector
from collections import deque
from ball_speed_methods import average, calc_speed, pixels_to_speed, distance_finder, focal_length, measure_ball, distance_from_between_points
import time


class DodgerTello:
    def __init__(self):
        """Class to encapsulate Tello object w/ its corresponding ML model
        
        Model is based on Yolov7 w/ training data created by me with images and
        labels pulled from Roboflow. Tello drone is operated roughly as a state
        machine with update states -> action(based on states) -> repeat.
        
        Note, delay in TCP video connection often causes ~1s delay in video feed.
        So, don't throw the ball to hard at the little guy!
        """
        # object detection
        self.model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')
        self.tello = Tello()
        self.cap = cv2.VideoCapture(VIDEO_URL)
        self.cap.open(VIDEO_URL) # grabbed, frame = capture.read()
        frame = self.cap.read()
        h, w = frame.shape
        self.im_center = {'x': (w/2), 'y': (h/2)}

        self.last_time = time.time()

        # save face data
        self.face_size = 0
        self.face_location = 0
        self.last_face_location = 0
        self.real_face_size = .35 # DOUBLE CHECK THIS VALUE

        # camera variables
        self.focal_length
        self.real_ball_size = 6.3 # cm

        # ball variables
        self.ball_size
        self.ball_location

        # variables for ball trackig
        self.last_dist = {'x': 0, 'y': 0, 'z': 0}
        self.change_in_dist_z = 0
        self.ball_pixels = 0

        self.speeds_x = deque((0, 0, 0), maxlen=3)
        self.speeds_y = deque((0, 0, 0), maxlen=3)
        self.speeds_z = deque((0, 0, 0), maxlen=3)
        self.avg_speed = {'x': 0, 'y': 0, 'z': 0}

        # takeoff sequecence as internal funct for asycio
        async def takeoff():
            await self.tello.wifi_wait_for_network(prompt=True)
            await self.tello.connect()
            await self.tello.takeoff()
        asyncio.run(takeoff())

    def update_object_variables(self):
        """Updates internal variables tracking faces and or tennis balls
        
        measurements are mildly averaged to handle noise and occasional 
        misidentificaitons with model. These internal variables are then used
        in the actions function to drive the Tello api calls
        """
        #TODO update sample time locations

        # process frame w/ model
        frame = self.cap.read()
        self.last_time = time.time() # <--- check this time samplig locatio
        detections = self.model(frame[..., ::-1])
        results = detections.pandas().xyxy[0].to_dict(orient="records")

        # process items found in frame
        face_counter = 0
        tennisball_in_frame = False
        if len(results) > 0:
            for result in results:
                # filter bad results
                if result['confidence'] >= .5:
                    
                    # Tennis ball calcs and identification
                    if result['name'] == 'Tennis-Ball':
                        tennisball_in_frame = True
                        measured_width_ball = int(result['xmax']) - int(result['xmin'])
                        measured_height_ball = int(result['ymax']) - int(result['ymin'])
                        # ball should be in square bound box. take average for ~ square dims in pixels
                        self.m_ball_size = (measured_width_ball + measured_height_ball) / 2
                        x = int((result['xmax'] + result['xmin']) / 2)
                        y = int((result['ymax'] + result['ymin']) / 2)
                        self.ball_location = {'x': x, 'y': y}
                        dist_meters_z = distance_finder(self.focal_length, self.real_ball_size, self.m_ball_size)

                        change_in_dist_z = self.last_dist['z'] - dist_meters_z
                        change_in_time = time.time() - self.last_time
                        # calculating the speed in of cords
                        self.speeds_z.append(calc_speed(change_in_dist_z, change_in_time))
                        self.speeds_x.append(pixels_to_speed('x', self.last_dist, self.ball_location,
                                                             self.m_ball_size, change_in_time))
                        self.speeds_y.append( -1 * pixels_to_speed('y', self.last_dist, self.ball_location,
                                                                   self.m_ball_size, change_in_time))

                        # average the speeds to damp noise
                        self.avg_speed['z'] = abs(average(self.speeds_z))
                        self.avg_speed['x'] = average(self.speeds_x)
                        self.avg_speed['y'] = average(self.speeds_y)

                        # save last values for next calcs
                        self.last_dist['z'] = dist_meters_z
                        self.last_dist['x'] = self.ball_location['x']
                        self.last_dist['y'] = self.ball_location['y']

                    # Face locating 
                    if result['name'] == 'face':
                        measured_width_face = int(result['xmax']) - int(result['xmin'])
                        measured_height_face = int(result['ymax']) - int(result['ymin'])
                        # ball should be in square bound box. take average for ~ square dims
                        curr_face_size = (measured_width_face + measured_height_face) / 2
                        x = int((result['xmax'] + result['xmin']) / 2)
                        y = int((result['ymax'] + result['ymin']) / 2)
                        curr_face_location = {'x': x, 'y': y}
                        if face_counter == 0:
                            self.face_size = curr_face_size
                            self.face_location = curr_face_location
                            face_dist_to_center = distance_from_between_points(curr_face_location, self.im_center)

                        # choose the face closest to camera center if multiple faces in frame
                        if face_counter >= 1:
                            curr_face_dist_to_center = distance_from_between_points(curr_face_location, self.im_center)
                            if curr_face_dist_to_center < face_dist_to_center:
                                self.face_size = curr_face_size
                                self.face_location = curr_face_location

                        self.face_x_dist = distance_finder(self.focal_length, self.real_face_size, self.face_size)
                        face_counter += 1
                        print("Troubleshooting. Face size is: ", self.face_size)

            if not tennisball_in_frame:
                self.avg_speed['z'] = 0
                self.avg_speed['x'] = 0
                self.avg_speed['y'] = 0

    def follow_face(self):
        """Funciton to handle how the Tello tracks and follows in frame face
        
        Tello will favor the face closest to the center of the screen to handle
        cases where multiple people are seen in frame. .follow_face() will have
        lower priority than dodge ball. Prioirty is implemented with order of TCP
        calls resulting in tello only listenting to most recent call
        """
        face_from_center = {'x':(self.face_location['x'] - self.im_center['x']),
                            'y':(self.face_location['y'] - self.im_center['y'])}
        dist_to_move = {'x':0, 'y':0, 'z':0}

        # turn towards face direciton
        if face_from_center['x'] > 20:
            asyncio.run(self.rotate_clockwise(5))
        elif face_from_center['x'] < 20:
            asyncio.run(self.rotate_c_clockwise(5))
            
        # adujust x coord based on face distance
        if self.face_x_dist <= 2.25:
            dist_to_move['x'] = -20
        elif self.face_x_dist >= 2.75:
            dist_to_move['x'] = 20
            
        # adjust y coords based on pixels
        if -face_from_center['y'] >= 30: # y coords are inversed in frame measures
            dist_to_move['y'] = -20
        elif -face_from_center['y'] <= 30:
            dist_to_move['y'] = 20
            
        self.tello.got_to(relative_position=Vector(dist_to_move['x'], # POTENTIALLY MAKE THIS A AWAIT FUNCITON
                                                   dist_to_move['y'],
                                                   dist_to_move['z']), speed=40)
                    

    def dodge_ball(self):
        pass

    def main(self):
        """Rough Drone statemachine"""
        self.update_object_variables()
        self.follow_face()
        self.dodge_ball()


    # Helper functions
    async def shutdown(self):
        try:
            await self.tello.land()
        finally:
            await self.tello.disconnect()

    async def rotate_clockwise(self, degrees: int):
        await self.tello.turn_clockwise(degrees)

    async def rotate_c_clockwise(self, degrees: int):
        await self.tello.turn_counterclockwise(degrees)


    def close_out(self):
        """Handles final Tello state when given signal to end sequence"""
        async def complete():
            try:
                await self.tello.land()
            finally:
                await self.tello.disconnect()
        asyncio.run(complete())
