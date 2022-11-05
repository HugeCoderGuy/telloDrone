import torch
import cv2
import asyncio
from tello_asyncio import Tello, VIDEO_URL


class DodgerTello:
    def __init__(self):
        # object detectio
        self.model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')
        self.tello = Tello()
        self.cap = cv2.VideoCapture(VIDEO_URL)
        self.cap.open(VIDEO_URL) # grabbed, frame = capture.read()

        async def takeoff():
            await self.tello.wifi_wait_for_network(prompt=True)
            await self.tello.connect()
            await self.tello.takeoff()
            await self.tello.land()
        asyncio.run(takeoff())

    def check_objects(self):
        frame = self.cap.read()
        objects = self.obj_detect(frame)
        if len(objects) > 0:
            for obj in objects:
                con = result['confidence']
                cs = result['class']
                x1 = int(result['xmin'])
                y1 = int(result['ymin'])
                x2 = int(result['xmax'])
                y2 = int(result['ymax'])

    def obj_detect(self, frame):
        detections = self.model(frame[..., ::-1])
        results = detections.pandas().xyxy[0].to_dict(orient="records")
        return results
        for result in results:
            con = result['confidence']
            cs = result['class']
            x1 = int(result['xmin'])
            y1 = int(result['ymin'])
            x2 = int(result['xmax'])
            y2 = int(result['ymax'])

    def close_out(self):
        async def complete():
            try:
                await self.tello.land()
            finally:
                await self.tello.disconnect()
        asyncio.run(complete())
