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

###### Hardware trigger setup  #####
# Open the camera 
tlf = pylon.TlFactory.GetInstance() #discover and connect to cameras  
cam = pylon.InstantCamera(tlf.CreateFirstDevice()) #creates camera object for the first camera to use settings and grab images
cam.Open() #Opens communication with the camera 

#Samples IO lines on each framestart trigger 
cam.ChunkModeActive.SetValue(True) #attach metadata to each image 
cam.ChunkSelector.SetValue("LineStatusAll") #metadata about IO line status for each image (state of TTL pulse)
cam.ChunkEnable.SetValue(True) #activates chunk you are interested in (LineStatus)
# print(cam.ChunkSelector.Symbolics) #lists other metadata you can collect with chunks 

# Set recording settings 
cam.Height.SetValue(600)
cam.Width.SetValue(800)
cam.ExposureTime.SetValue(3000)
cam.AcquisitionFrameRateEnable.SetValue(True)
cam.AcquisitionFrameRate.SetValue(200)
cam.GainAuto.SetValue("Continuous")

# Start camera image acquisition and stop after 1000 frames, and records the I/O status per frame 
# In this section, "res" is a variable that holds a single grab result object (frame, metadata, was grab successful, frame num, camera ID)
# cam.RetrieveResult returns the result of the camera at 1000 ms- if there is no frame there's nothing there
cam.StartGrabbingMax(1000)

io_res = [] #initialize an empty list to store the timestamp and I/O status 
while cam.IsGrabbing(): # Runs as long as the camera is grabbing images 
    with cam.RetrieveResult(1000) as res: # Returns an error or none if there isn't a frame
        time_stamp = res.TimeStamp #Get the timestamp for the frame grabbed
        io_res.append((time_stamp, res.ChunkLineStatusAll.Value)) #Attach the metadata from the chunk to the frame 

cam.StopGrabbing () 


# Plot I/O line values 
# Convert to numpy array 
io_array = np.array(io_res)
# Extract first column timestamps
x_vals = io_array[:,0]
# Start with first timestamp as '0' 
x_vals -= x_vals[0]

# Extract second column into io values 
y_vals = io_array[:,1]
# For each bit plot the graph 
for bit in range(8): 

    logic_level = ((y_vals & (1<<bit)) != 0)*0.8 +bit
    #plot in seconds
    plt.plot(x_vals / 1e9, logic_level, label = bit)

plt.xlabel("time [s]")
plt.ylabel("IO_LINE [#]")
plt.legend()
plt.show()

# Grab with a hardware trigger on line 3

# Load the default camera configuration 
cam.UserSetSelector.Value = "Default"
cam.UserSetLoad.Execute()
# cam.UserSetSave.Execute() # Use to define and save your own settings 


# Setup the trigger/acquisition controls 
cam.TriggerSelector.SetValue("FrameStart")
cam.TriggerSource.SetValue("Line3")
cam.TriggerMode.SetValue("On")
print(cam.TriggerActivation.Value)

# res = cam.GrabOne(py.waitForever) # use if not using background loop 

# Background loop 
# Definition of event handler class
class TriggeredImage(pylon.ImageEventHandler):
    def __init__(self):
        super().__init__()
        self.grab_times = []
    def OnImageGrabbed(self, camera, grabResult): 
        self.grab_times.append(grabResult.TimeStamp)

# Create event handler instance 
image_timestamps = TriggeredImage()

# Register handler 
# Remove all other handlers 
cam.RegisterImageEventHandler(image_timestamps, 
                              pylon.RegistrationMode_ReplaceAll, 
                              pylon.Cleanup_None)

# Start grabbing with background loop
cam.StartGrabbingMax(100, pylon.GrabStrategy_LatestImages, pylon.GrabLoop_ProvidedByInstantCamera)
while cam.IsGrabbing():
    time.sleep(0.1)
# Stop grabbing 
cam.StopGrabbing()


np.diff(image_timestamps.grab_times)

frame_delta_s = np.diff(np.array(image_timestamps.grab_times))/1.e9
plt.plot(frame_delta_s, ".")
plt.axhline(np.mean(frame_delta_s))
plt.show()

plt.hist(frame_delta_s - np.mean(frame_delta_s), bins=100)
plt.xticks(rotation=45)
plt.show()

cam.Close()