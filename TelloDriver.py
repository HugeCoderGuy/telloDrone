import torch
import cv2
import asyncio
from collections import deque
from ball_speed_methods import average, calc_speed, pixels_to_speed, distance_finder, focal_length, measure_ball, distance_from_between_points
import time
from Controller import Controller
from DroneEnum import DroneEnum


#TODO Make sure the .main() has a finally statement that closes out the drone connection
class TelloDriver():
    def __init__(self, frame):
        """Class to encapsulate Tello object w/ its corresponding ML model

        Model is based on Yolov7 w/ training data created by me with images and
        labels pulled from Roboflow. Tello drone is operated roughly as a state
        machine with update states -> action(based on states) -> repeat.

        Note, delay in TCP video connection often causes ~1s delay in video feed.
        So, don't throw the ball to hard at the little guy!
        """
        # h, w = frame.shape[:2]
        h = 720
        w = 960
        # print('IMAGE SIZE IS: ', h, w)
        self.im_center = {'x': (w/2), 'y': (h/2)}

        self.time_tracker = deque([time.time()])

        # save face data
        self.face_size = 0
        self.face_location = {'x': (w/2), 'y': (h/2)}
        self.face_x_dist = 1.5
        self.last_face_location = 0
        self.real_face_size = 13 # face is ~35cm
        self.new_face = False

        # camera variables
        self.focal_length = 1000
        self.real_ball_size = 6.3 # cm

        # ball variables
        self.ball_location = {'x': 0, 'y': 0}
        self.tennisball_in_frame = False

        # variables for ball trackig
        self.last_dist = {'x': 0, 'y': 0, 'z': 0}
        self.change_in_dist_z = 0
        self.ball_pixels = 0

        self.speeds_x = deque((0, 0, 0), maxlen=3)
        self.speeds_y = deque((0, 0, 0), maxlen=3)
        self.speeds_z = deque((0, 0, 0), maxlen=3)
        self.avg_speed = {'x': 0, 'y': 0, 'z': 0}


    def update_object_variables(self, results):
        """Updates internal variables tracking faces and or tennis balls

        measurements are mildly averaged to handle noise and occasional
        misidentificaitons with model. These internal variables are then used
        in the actions function to drive the Tello api calls
        """

        # process frame w/ model
        self.time_tracker.appendleft(time.time())

        # process items found in frame
        face_counter = 0
        self.tennisball_in_frame = False
        if len(results) > 0:
            for result in results:
                # filter bad results

                # Tennis ball calcs and identification
                # if result['name'] == 'Tennis-Ball':
                if result['name'] == 'delete this line later':
                    if result['confidence'] >= .5:
                        self.tennisball_in_frame = True
                        measured_width_ball = int(result['xmax']) - int(result['xmin'])
                        measured_height_ball = int(result['ymax']) - int(result['ymin'])
                        # ball should be in square bound box. take average for ~ square dims in pixels
                        self.m_ball_size = (measured_width_ball + measured_height_ball) / 2
                        x = int((result['xmax'] + result['xmin']) / 2)
                        y = int((result['ymax'] + result['ymin']) / 2)
                        self.ball_location = {'x': x, 'y': y}
                        dist_meters_z = distance_finder(self.focal_length, self.real_ball_size, self.m_ball_size)

                        change_in_dist_z = self.last_dist['z'] - dist_meters_z
                        change_in_time = self.time_tracker[0] - self.time_tracker.pop()
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
                    if result['confidence'] >= .3:
                        measured_width_face = int(result['xmax']) - int(result['xmin'])
                        measured_height_face = int(result['ymax']) - int(result['ymin'])
                        print('faces are', measured_height_face, measured_width_face)
                        # ball should be in square bound box. take average for ~ square dims
                        curr_face_size = measured_width_face  # (measured_width_face + measured_height_face) / 2
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
                        self.new_face = True


            if not self.tennisball_in_frame:
                self.avg_speed['z'] = 0
                self.avg_speed['x'] = 0
                self.avg_speed['y'] = 0

    def follow_face(self) -> int:
        """Follows face closest to center of screen
        
        .update_object_variables() filters faces that are further from
        the center of the screen. 

        Returns:
            int: value corresponding to Drone action enum
        """
        if self.new_face:
            self.new_face = False
            face_from_center = {'x':(self.face_location['x'] - self.im_center['x']),
                                'y':(self.face_location['y'] - self.im_center['y'])}
            print('face vars:', face_from_center, self.face_x_dist)

            # turn towards face direciton
            if face_from_center['x'] > 125:
                return DroneEnum.clockwise.value
            elif face_from_center['x'] < -125:
                return DroneEnum.counter_clockwise.value

            # adjust y coords based on pixels
            if -face_from_center['y'] >= 315: # y coords are inversed in frame measures
                return DroneEnum.up.value
            elif -face_from_center['y'] <= -25:
                return DroneEnum.down.value

            # adujust x coord based on face distance
            if self.face_x_dist <= .9:
                return DroneEnum.backward.value
            elif self.face_x_dist >= 1.5 and self.face_x_dist < 4:
                return DroneEnum.forward.value
            

        
        # everything else checks out, don't send any tello commands
        return 0
            
                
    def dodge_ball(self) -> int:
        """Uses internal variables to tell drone to dodge or not

        Returns:
            int: returns value corresponding with drone commands Enum
        """
        if self.last_dist['z'] <= 3 and self.avg_speed['z'] > 1:
            ball_from_center = {'x': (self.ball_location['x'] - self.im_center['x']),
                                'y': (self.ball_location['y'] - self.im_center['y'])}
            if (ball_from_center['x'] < 50 and ball_from_center['x'] > -50) and ball_from_center['y'] < 50:
                return DroneEnum.dodge_up.value
            if ball_from_center['x'] < 0:
                return DroneEnum.dodge_right.value
            if ball_from_center['x'] > 0:
                return DroneEnum.dodge_left.value
            
        # default
        return 0



