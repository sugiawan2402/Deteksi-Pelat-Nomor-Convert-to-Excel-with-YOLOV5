import argparse
import time
from pathlib import Path

import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

import numpy as np
import pytesseract
from PIL import Image
from pytesseract import image_to_string

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path, save_one_box
from utils.plots import colors, plot_one_box
from utils.torch_utils import select_device, load_classifier, time_synchronized
import csv
from datetime import datetime

def markAttendance(name):
    with open('Attendance.csv', 'r+') as f:
        myDataList = f.readlines()
        # print(myDataList)
        nameList = []
        for line in myDataList:
            entry = line.split('\n')
            # print('entry : ',entry)
            nameList.append(entry[0])
            if name not in nameList:
                # print('name : ', name)
                now = datetime.now()
                dtString = now.strftime('%H:%M:%S')
                f.writelines(f'\n plat : {name} == jam masuk : {dtString}')


def detect(opt):
    source, weights, view_img, imgsz = opt.source, opt.weights, opt.view_img, opt.img_size
    # save_img = not opt.nosave and not source.endswith('.txt')  # save inference images
    webcam = source.isnumeric() or source.endswith('.txt') or source.lower().startswith(
        ('rtsp://', 'rtmp://', 'http://', 'https://'))
    
    # Directories
    # save_dir = increment_path(Path(opt.project) / opt.name, exist_ok=opt.exist_ok)  # increment run
    # (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir
    
    # Initialize
    set_logging()
    device = select_device(opt.device)
    half = device.type != 'cpu'  # half precision only supported on CUDA
    
    # Load model
    model = attempt_load(weights, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size
    names = model.module.names if hasattr(model, 'module') else model.names  # get class names
    if half:
        model.half()  # to FP16
    
    # Second-stage classifier
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model']).to(device).eval()
    
    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam:
        view_img = check_imshow()
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz, stride=stride)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride)
    
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    t0 = time.time()
    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        
        # Inference
        t1 = time_synchronized()
        pred = model(img, augment=opt.augment)[0]
        
        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = time_synchronized()
        
        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # print(pred)
        # Process detections
        pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
        for i, det in enumerate(pred):  # detections per image
            if webcam:
                p, s, im0, frame = path[i], '%g: ' % i, im0s[i].copy(), dataset.count
            else:
                p, s, im0, frame = path, '', im0s.copy(), getattr(dataset, 'frame', 0)
            
            p = Path(p)  # to Path
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()
                
                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string
                
                # Write results
                for *xyxy, conf, cls in reversed(det):
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()
                    x, y, h, w = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])

                    cv2.rectangle(im0, (x, y), (h, w), (245, 90, 24) , 2)
                    crop = im0 [y:w, x:h]
                    cv2.imshow('crop', crop)
                    
                    resize = cv2.resize(crop, (412, 320), interpolation = cv2.INTER_AREA)
                    gray = cv2.cvtColor(resize, cv2.COLOR_BGR2GRAY)  # convert to grey scale
                    gray = cv2.bilateralFilter(gray, 11, 17, 17)
                    # cv2.imshow("resize", gray)

                    name = pytesseract.image_to_string(gray, lang='eng', config='--psm 6')
                    # name = pytesseract.image_to_string(gray,
                    #                                    config='-l eng --oem 1 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')
                    print('name22 = ', name)
                    markAttendance(name)

            frame2 = cv2.resize(im0, (640, 480))
            cv2.imshow(str(p), im0)
            k =cv2.waitKey(1)  # 1 millisecond
            # k = cv2.waitKey(1) & 0xFF
            if k == ord("a"):
                name1 = 'resa'
                print(name1)
                markAttendance(name1)
            if k == ord("s"):
                name1 = 'pamilianto'
                print(name1)
                markAttendance(name1)
            
            
    
    
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default="weights/best.pt", help='model.pt path(s)')
    parser.add_argument('--source', type=str, default= 'vidd.mp4',  help='source')  # file/folder, 0 for webcam
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--conf-thres', type=float, default=0.40, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.35, help='IOU threshold for NMS')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    opt = parser.parse_args()
    with torch.no_grad():
        detect(opt=opt)