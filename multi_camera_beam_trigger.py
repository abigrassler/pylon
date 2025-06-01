# To make sure you are in the right environment: 
# 1. Open script in VS code 
# 2. Open the command palette (Ctrl+Shift+P)
# 3. Type in: Python: Select Interpreter
# 4. Select environment set up for pypylon (mine is basler_env)


from pypylon import pylon
from datetime import datetime
from pypylon import genicam
import numpy as np
import pypylon.genicam as geni
import matplotlib.pyplot as plt
import cv2
import os
import time
import pandas as pd


##### Define a function to start and stop grabbing images with a TTL pulse #####
def grab_during_ttl(cam_array, converter, video_writer, metadata_list, trigger_line_bit=3):
    """Grabs frames while TTL (beam break) line is high.
    
    Args:
        cam_array: Open and configured Pylon camera.
        converter: ImageFormatConverter object.
        video_writer: OpenCV VideoWriter object.
        metadata_list: list to append (timestamp, line_status, counter_value).
        trigger_line_bit: Which digital line to monitor (default is Line3 → bit 3).
    """

    cam_array.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByUser)
    print("Waiting for TTL HIGH to begin recording...")

    grabbing = False

    while cam_array.IsGrabbing():
        try: 
            with cam_array.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException) as grab:
                if not grab.GrabSucceeded():
                    continue

                # Read chunk data
                timestamp = grab.ChunkTimestamp
                line_status = grab.ChunkLineStatusAll.Value
                counter_val = grab.ChunkCounterValue.Value
                ttl_state = (line_status >> trigger_line_bit) & 1

                if ttl_state and not grabbing:
                    print("TTL HIGH detected. Starting frame capture.")
                    grabbing = True

                if grabbing:
                    frame = converter.Convert(grab).GetArray()
                    video_writer.write(frame)
                    metadata_list.append((timestamp, line_status, counter_val))
                    print(f"Grabbed frame at timestamp {timestamp}, TTL state: {ttl_state}") 

                    if not ttl_state:
                        print("TTL LOW detected. Stopping capture.")
                        break  # Stop when TTL falls
        except genicam.TimeoutException:
            print("No frame received — probably no trigger")
    cam_array.StopGrabbing()

##### Multicamera setup #####

#   Provide number of cameras in setup 
num_cameras = 4

# Create output folder
camera_names = ["camA", "camB", "camC", "camD"]
general_dir = r"D:\abi_data\raw_data\setup\test_cameras"

for camera_ID in camera_names: 
    camera_dir = os.path.join(general_dir, camera_ID)
    os.makedirs(camera_dir, exist_ok=True)
    filename = f"{camera_ID}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.avi"
    video_path = os.path.join(camera_dir, filename)

# Discover and connect to camera
tlf = pylon.TlFactory.GetInstance() #discover and connect to cameras 

# List all available devices
devices = tlf.EnumerateDevices()

# Creates an array of cameras (objects) for handling multiple cameras.
cam_array = pylon.InstantCameraArray(num_cameras)

# Maps each camera slot in the cam_array to a real, connected camera device.
for idx, cam in enumerate(cam_array): 
    cam.Attach(tlf.CreateDevice(devices[idx]))
    cam.Attach(tlf.CreateDevice(devices[idx]))
    cam.Open()
    cam.UserSetSelector.Value = "Default"
    cam.UserSetLoad.Execute()

    # Set the chunks you want (metadata). Here we want to sample IO lines on each framestart trigger  
    chunks = ["LineStatusAll", "Timestamp", "CounterValue"]
    cam.ChunkModeActive.SetValue(True) #attach metadata to each image 
    for chunk in chunks:
        cam.ChunkSelector.SetValue(chunk) #metadata about IO line status for each image (state of TTL pulse)
        if chunk == "CounterValue": 
            cam.CounterSelector.SetValue("Counter1")
        cam.CounterEventSource.SetValue("FrameStart")
        cam.ChunkEnable.SetValue(True) #activates chunk you are interested in (LineStatus)
    # Confirm chunk is enabled
        #is_enabled = cam.ChunkEnable.GetValue()
        #print(f"Chunk '{chunk}': {'ENABLED' if is_enabled else 'disabled'}")
    

    # Set image quality and format settings 
    cam.Height.SetValue(600)
    cam.Width.SetValue(800)
    cam.ExposureTime.SetValue(3000)
    cam.AcquisitionFrameRateEnable.SetValue(True)
    cam.AcquisitionFrameRate.SetValue(200)
    cam.GainAuto.SetValue("Continuous")

    # Setup the trigger/acquisition controls 
    cam.TriggerSelector.SetValue("FrameStart")
    cam.TriggerActivation.SetValue("RisingEdge")
    cam.TriggerSource.SetValue("Line3")
    cam.TriggerMode.SetValue("On")

# Create an image format converter
converter = pylon.ImageFormatConverter()
converter.OutputPixelFormat = pylon.PixelType_BGR8packed  # For OpenCV (color)
converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

# try:
#     while True:
#         #timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
#         #filename = f"camA_{timestamp}.avi"
#         #video_path = os.path.join(camera_dir, filename)
#         filename 
#         video_path

#         video_writer = cv2.VideoWriter(
#             video_path,
#             cv2.VideoWriter_fourcc(*'XVID'),
#             200.0,
#             (800, 600)
#         )

#         metadata = []
#         grab_during_ttl(cam_array, converter, video_writer, metadata)

#         # Save metadata
#         metadata_filename = f"metadata_{timestamp}.csv"
#         metadata_path = os.path.join(camera_dir, metadata_filename)
#         df = pd.DataFrame(metadata, columns=["Timestamp_ns", "LineStatusAll", "CounterValue"])
#         df.to_csv(metadata_path, index=False)

#         video_writer.release()
# except KeyboardInterrupt:
#     print("Recording stopped by user.")
# finally:
#     cam_array.Close()
#     cv2.destroyAllWindows()





