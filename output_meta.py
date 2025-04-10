import argparse
import sys
from functools import lru_cache

import numpy as np

from datetime import datetime

import json

from picamera2 import MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import (NetworkIntrinsics, postprocess_nanodet_detection)

from pathlib import Path

last_detections = []


class Detection:
    def __init__(self, coords, category, conf, metadata):
        """Create a Detection object, recording the bounding box, category and confidence."""
        self.category = category
        self.conf = conf
        self.box = imx500.convert_inference_coords(coords, metadata, picam2)

def float32_to_float(obj):
    if isinstance(obj, np.float32):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: float32_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [float32_to_float(x) for x in obj]
    return obj

def parse_detections(metadata: dict):
    global last_detections
    bbox_normalization = intrinsics.bbox_normalization
    threshold = args.threshold
    iou = args.iou
    max_detections = args.max_detections
    np_outputs = imx500.get_outputs(metadata, add_batch=True)
    input_w, input_h = imx500.get_input_size()
    
    if np_outputs is None:
        return last_detections
        
    if intrinsics.postprocess == "nanodet":
        boxes, scores, classes = \
            postprocess_nanodet_detection(outputs=np_outputs[0], conf=threshold, iou_thres=iou, max_out_dets=max_detections)[0]
        from picamera2.devices.imx500.postprocess import scale_boxes
        boxes = scale_boxes(boxes, 1, 1, input_h, input_w, False, False)
    else:
        boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]

    if bbox_normalization:
        boxes = boxes / input_h

    boxes = np.array_split(boxes, 4, axis=1)
    boxes = zip(*boxes)
    
    last_detections = [
        Detection(box, category, score, metadata)
        for box, score, category in zip(boxes, scores, classes)
        if score > threshold
    ]

    # 現在の日時を取得
    now = datetime.now()

    # YYYYmmDDHHMMSSsss形式にフォーマット
    formatted_time = now.strftime('%Y%m%d%H%M%S%f')[:-3]
    
    # 検出結果をまとめるための辞書を作成
    detection_result = {
        "time": formatted_time,
        "detections": []
    }
    
    # 各検出結果を変換してリストに追加
    labels = get_labels()
    for detection in last_detections:
        detection_data = {
            "label": labels[int(detection.category)],
            "confidence": float(detection.conf),  # numpy.float32をfloatに変換
            "left": float(640-detection.box[0]),
            "top": float(detection.box[1]),
            "right": float(640- detection.box[0] - detection.box[2]),
            "bottom": float(detection.box[1] + detection.box[3])
        }
        detection_result["detections"].append(detection_data)
    
    # JSONファイルとして保存
    home = Path.home()
    temp_dir = home / 'temp'

    if not temp_dir.exists():
        temp_dir.mkdir()

    with open(temp_dir / f'{formatted_time}.json', 'w', encoding='utf-8') as f:
        json.dump(detection_result, f, ensure_ascii=False, indent=4)
    
    return last_detections

@lru_cache
def get_labels():
    labels = intrinsics.labels

    if intrinsics.ignore_dash_labels:
        labels = [label for label in labels if label and label != "-"]
    return labels

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, help="Path of the model", default="/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk")
    parser.add_argument("--fps", type=float, default=7, help="Frames per second")
    parser.add_argument("--bbox-normalization", action=argparse.BooleanOptionalAction, help="Normalize bbox")
    parser.add_argument("--threshold", type=float, default=0.40, help="Detection threshold")
    parser.add_argument("--iou", type=float, default=0.60, help="Set iou threshold")
    parser.add_argument("--max-detections", type=int, default=40, help="Set max detections")
    parser.add_argument("--ignore-dash-labels", action=argparse.BooleanOptionalAction, help="Remove '-' labels ")
    parser.add_argument("--postprocess", choices=["", "nanodet"], default=None, help="Run post process of type")
    parser.add_argument("-r", "--preserve-aspect-ratio", action=argparse.BooleanOptionalAction, help="preserve the pixel aspect ratio of the input tensor")
    parser.add_argument("--labels", type=str, help="Path to the labels file")
    parser.add_argument("--print-intrinsics", action="store_true", help="Print JSON network_intrinsics then exit")
    parser.add_argument("--bbox-order", choices=["yx", "xy"], default="yx", help="Set bbox order yx -> (y0, x0, y1, x1) xy -> (x0, y0, x1, y1)")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    # This must be called before instantiation of Picamera2
    imx500 = IMX500(args.model)
    intrinsics = imx500.network_intrinsics

    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "object detection"
    elif intrinsics.task != "object detection":
        print("Network is not an object detection task", file=sys.stderr)
        exit()

    # Override intrinsics from args
    for key, value in vars(args).items():
        if key == 'labels' and value is not None:
            with open(value, 'r') as f:
                intrinsics.labels = f.read().splitlines()
        elif hasattr(intrinsics, key) and value is not None:
            setattr(intrinsics, key, value)

    # Defaults
    if intrinsics.labels is None:
        with open("./coco_labels.txt", "r") as f:
            intrinsics.labels = f.read().splitlindeaes()
    intrinsics.update_with_defaults()

    if args.print_intrinsics:
        print(intrinsics)
        exit()

    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration(controls={"FrameRate": intrinsics.inference_rate}, buffer_count=12)

    imx500.show_network_fw_progress_bar()
    picam2.start(config, show_preview=False)

    if intrinsics.preserve_aspect_ratio:
        imx500.set_auto_aspect_ratio()

    last_results = None

    while True:
        last_results = parse_detections(picam2.capture_metadata())
