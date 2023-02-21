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
    print(result)
    con = result['confidence']
    cs = result['class']
    x1 = int(result['xmin'])
    y1 = int(result['ymin'])
    x2 = int(result['xmax'])
    y2 = int(result['ymax'])
    # Do whatever you want


# result like:
# {'xmin': 802.948486328125, 'ymin': 157.6776580810547, 'xmax': 951.4849853515625, 'ymax': 304.49725341796875, 'confidence': 0.9613910913467407, 'class': 0, 'name': 'Tennis-Ball'}
# {'xmin': 414.9276123046875, 'ymin': 3.1645660400390625, 'xmax': 748.3037109375, 'ymax': 368.46624755859375, 'confidence': 0.9311182498931885, 'class': 1, 'name': 'face'}