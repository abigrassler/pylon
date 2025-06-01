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


##### function to start and stop grabbing images with a TTL pulse #####
def grab_during_ttl(cam, converter, video_writer, metadata_list, trigger_line_bit=3):
    """Grabs frames while TTL (beam break) line is high.
    
    Args:
        cam: Open and configured Pylon camera.
        converter: ImageFormatConverter object.
        video_writer: OpenCV VideoWriter object.
        metadata_list: list to append (timestamp, line_status, counter_value).
        trigger_line_bit: Which digital line to monitor (default is Line3 → bit 3).
    """

    cam.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByUser) # Starts a steady stream of images, provides 1 frame at a time when triggered 
    print("Waiting for TTL HIGH to begin recording...")

    grabbing = False # Do not start recording the images yet- no TTL pulse yet.

    while cam.IsGrabbing(): # When the camera is on and sending frames, do the following
        try: # Test a block of code for errors 
            with cam.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException) as grab: #wait for the next frame that should be recorded,. If no frame is recieved in 10000ms raise timeout exception error. Depends on whether TTL pulse was triggered.  
                if not grab.GrabSucceeded(): #if there is no frame, then 
                    continue #go on to the next line

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
    cam.StopGrabbing()


##### Load, rest if needed, and open the camera ####

# Discover and connect to camera
tlf = pylon.TlFactory.GetInstance() #discover and connect to cameras  
cam = pylon.InstantCamera(tlf.CreateFirstDevice()) #creates device on the computer for the first camera identified 
cam.Open() #Opens communication with the camera 

# Load the default camera configuration 
cam.UserSetSelector.Value = "Default"
cam.UserSetLoad.Execute()
# cam.UserSetSave.Execute() # Use to define and save your own settings 


##### Set configurations for cameras ##### 

# Select recording settings
camera_dir = r"D:\abi_data\raw_data\setup\test_cameras\camA" # Create output folder
os.makedirs(camera_dir, exist_ok=True) 
filename = f"camA_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.avi"
video_path = os.path.join(camera_dir, filename)

# Set the chunks you want (metadata). Here we want to sample IO lines on each framestart trigger 
#print(cam.ChunkSelector.Symbolics) #lists other metadata you can collect with chunks 
chunks = ["LineStatusAll", "Timestamp", "CounterValue"]
cam.ChunkModeActive.SetValue(True) #attach metadata to each image 
for chunk in chunks:
    cam.ChunkSelector.SetValue(chunk) #metadata about IO line status for each image (state of TTL pulse)
    if chunk == "CounterValue": 
     cam.CounterSelector.SetValue("Counter1")
     cam.CounterEventSource.SetValue("FrameStart")
    cam.ChunkEnable.SetValue(True) #activates chunk you are interested in (LineStatus)
# Confirm chunk is enabled
    is_enabled = cam.ChunkEnable.GetValue()
    print(f"Chunk '{chunk}': {'ENABLED' if is_enabled else 'disabled'}")
#metadata = [] #use to save metadata values 

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

try:
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"camA_{timestamp}.avi"
        video_path = os.path.join(camera_dir, filename)

        video_writer = cv2.VideoWriter(
            video_path,
            cv2.VideoWriter_fourcc(*'XVID'),
            200.0,
            (800, 600)
        )

        metadata = []
        grab_during_ttl(cam, converter, video_writer, metadata)

        # Save metadata
        metadata_filename = f"metadata_{timestamp}.csv"
        metadata_path = os.path.join(camera_dir, metadata_filename)
        df = pd.DataFrame(metadata, columns=["Timestamp_ns", "LineStatusAll", "CounterValue"])
        df.to_csv(metadata_path, index=False)

        video_writer.release()
except KeyboardInterrupt:
    print("Recording stopped by user.")
finally:
    cam.Close()
    cv2.destroyAllWindows()
