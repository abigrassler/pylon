from pypylon import pylon
from datetime import datetime
import numpy as np
import pypylon as py
import pypylon.genicam as geni
import matplotlib.pyplot as plt
import cv2
import os
import time
import pandas as pd


###### Multicamera setup #######
#   Provide number of cameras in setup 
num_cameras = 4

# Create output folder
camera_names = ["\camA", "\camB", "\camC", "\camD"]
for camera_ID in camera_names: 
    #print(camera_ID)
    general_dir = r"D:\abi_data\raw_data\setup\test_cameras"
    camera_dir = general_dir + camera_ID
    #print(camera_dir)
    os.makedirs(camera_dir, exist_ok=True)

# Get the singleton instance of the transport layer factory (TLF)
# This is the part of the Pylon software that communicates with the camera hardware 
tlf = pylon.TlFactory.GetInstance()

# List all available devices
devices = tlf.EnumerateDevices()
# Print out device names
#for device in devices:
    #print(device.GetModelName(), device.GetSerialNumber())

# Creates an array of cameras (objects) for handling multiple cameras.
cam_array = pylon.InstantCameraArray(num_cameras)

# Maps each camera slot in the cam_array to a real, connected camera device.
for idx, cam in enumerate(cam_array): 
    cam.Attach(tlf.CreateDevice(devices[idx]))
# Opens real cameras 
cam_array.Open()

# Create a list of the camera names you want to use if you don't want to use the serial numbers
camera_labels = ["camA", "camB", "camC", "camD"]

# Store a unique ID for each camera to identify incoming images and set exposure time for each camera 
for idx, cam in enumerate(cam_array): 
    label = camera_labels[idx] 
    cam.SetCameraContext(idx)
    print(f"set context {idx} for camera {label}")
    cam.SetCameraContext(idx)
    print(f"Setting exposure for camera {label}")
    cam.ExposureTime.SetValue(3000)


######## test to grab 10 frames with multiple cameras #########
# Have each camera grab 10 frames 
frames_to_grab = 10 
# Store last framecount in array 
frame_counts = [0]*num_cameras

print(frame_counts)

frame_counts = [0] * num_cameras

cam_array.StartGrabbing()
while True:
   with cam_array.RetrieveResult(1000) as res:
       if res.GrabSucceeded():
           cam_id = res.GetCameraContext()
           frame_counts[cam_id] += 1
           print(f"cam #{cam_id}  count #{frame_counts[cam_id]}")
            
            # Optional: save or display the image here

           if all(count >= frames_to_grab for count in frame_counts):
               print(f"All cameras have acquired {frames_to_grab} frames")
               break
cam_array.StopGrabbing()
cam_array.Close()
print("Final frame counts:", frame_counts)