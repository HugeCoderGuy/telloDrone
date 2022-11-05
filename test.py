import torch
import cv2
model = torch.hub.load('WongKinYiu/yolov7', 'custom', 'yolov7/best.pt')
camera = cv2.VideoCapture(0)
ret, frame = camera.read()
# frame = cv2.imread('./yolov7/tello/test/images/0ad90195-cd77-489e-bf85-08c83b80d3e0_jpg.rf.edac59328c5bf3a7e596b0636aa6ebc7')
print(frame)
detections = model(frame[..., ::-1])
results = detections.pandas().xyxy[0].to_dict(orient="records")
print(results)
for result in results:
    con = result['confidence']
    cs = result['class']
    x1 = int(result['xmin'])
    y1 = int(result['ymin'])
    x2 = int(result['xmax'])
    y2 = int(result['ymax'])
    # Do whatever you want


# result like:
# [{'xmin': 541.2117919921875, 'ymin': 178.4976348876953, 'xmax': 797.6717529296875, 'ymax': 511.9945068359375, 'confidence': 0.9488492608070374, 'class': 1, 'name': 'face'}]
