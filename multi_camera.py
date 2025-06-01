import cv2
import enum
import itertools
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pypylon import pylon, genicam
from datetime import datetime, timedelta

class Camera:
  def __init__(self, name):
    self.name = name
    self.output_directory = os.path.join('D', os.path.sep, 'abi_data', 'raw_data', 'setup', 'test_cameras', self.name)
    self.metadata = []
    self.video_timestamp = None

    # We'll start a new video whenever the beam is broken, so just make a placeh
    self.video_writer: cv2.VideoWriter = None

    os.makedirs(self.output_directory, exist_ok=True)


class Context:
  def __init__(self):
    self.cameras = [
      Camera('camA'),
      Camera('camB'),
      Camera('camC'),
      Camera('camD')
    ]
    self.num_cameras = len(self.cameras)
    self.trigger_line = 3
    self.trigger_line_id = f'Line{self.trigger_line}'
    self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
    self.frame_rate = 200.0
    self.sampling_rate = 1.0 / self.frame_rate
    self.output_resolution = (800, 600)

    # The cameras are triggered by an Arduino; when we don't get triggered within a certain amount of time, we assume the beam
    # has become unbroken
    self.frame_timestamp = 0
    self.max_frame_delta = timedelta(seconds=self.sampling_rate * 1.5)

    # Create an image format converter. This is used to convert the raw frames to something that can be written to a video
    self.converter = pylon.ImageFormatConverter()
    self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed  # For OpenCV (color)
    self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    # Discover and connect to camera
    tlf = pylon.TlFactory.GetInstance()

    # For multuple cameras: 
    devices = tlf.EnumerateDevices([])
    self.cam_array = pylon.InstantCameraArray(self.num_cameras)
    for idx, camera in enumerate(self.cam_array):
      camera.Attach(tlf.CreateDevice(devices[idx]))
      camera.Open()

      # Load the default camera configuration 
      camera.UserSetSelector.Value = "Default"
      camera.UserSetLoad.Execute()

      # Set the chunks you want (metadata). Here we want to sample IO lines on each framestart trigger 
      chunks = ["LineStatusAll", "Timestamp", "CounterValue"]
      camera.ChunkModeActive.SetValue(True) #attach metadata to each image 
      for chunk in chunks:
        camera.ChunkSelector.SetValue(chunk) #metadata about IO line status for each image (state of TTL pulse)
        if chunk == "CounterValue":
          camera.CounterSelector.SetValue("Counter1")
          camera.CounterEventSource.SetValue("FrameStart")
        camera.ChunkEnable.SetValue(True) #activates chunk you are interested in (LineStatus)

        if not camera.ChunkEnable.GetValue():
          print(f'Tried to enable chunk {chunk} for camera {camera.name}, but it reported as disabled')

      # Set image quality and format settings 
      camera.Height.SetValue(600)
      camera.Width.SetValue(800)
      camera.ExposureTime.SetValue(3000)
      camera.AcquisitionFrameRateEnable.SetValue(True)
      camera.AcquisitionFrameRate.SetValue(200)
      camera.GainAuto.SetValue("Continuous")

      # Setup the trigger/acquisition controls 
      camera.TriggerSelector.SetValue("FrameStart")
      camera.TriggerActivation.SetValue("RisingEdge")
      camera.TriggerSource.SetValue(self.trigger_line_id)
      camera.TriggerMode.SetValue("On")

  def run_loop(self):
    self.cam_array.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByUser) # Starts a steady stream of images, provides 1 frame at a time when triggered 
    
    try:
      while True:
        grab = self.cam_array.RetrieveResult(pylon.waitForever, pylon.TimeoutHandling_Return)

        frame_delta = grab.GetTimeStamp() - self.frame_timestamp
        max_frame_delta = self.max_frame_delta.total_seconds() * (10 ** 9) # Convert our delta from seconds to nanoseconds

        if frame_delta > max_frame_delta:
          print(f'Frame delta exceeded; delta = {frame_delta}, max delta = {max_frame_delta}; assuming beam status changed and starting a new video')

          # If this is our first video, there's no current video to finalize
          if self.video_writer:
            print('Finishing previous video')
            self.video_writer.release()

            file_name = f'metadata_{self.video_timestamp}'
            file_path = os.path.join(self.camera_dir, file_name)
            df = pd.DataFrame(self.metadata, columns=["Timestamp_ns", "LineStatusAll", "CounterValue"])
            df.to_csv(file_path, index=False)

          # Start a new video
          self.video_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
          for camera_ID in camera_names: 
            filename = f"{camera_ID}_{self.video_timestamp}.avi"
            file_path = os.path.join(camera_dir, filename)

          print(f'Starting new video at {file_path}')

          self.video_writer = cv2.VideoWriter(
            file_path,
            self.fourcc,
            self.frame_rate,
            self.output_resolution
          )

          self.metadata = []

        self.frame_timestamp = grab.GetTimeStamp()

        frame = self.converter.Convert(grab).GetArray()
        self.video_writer.write(frame)

        metadata = (
          grab.ChunkTimestamp.Value,
          grab.ChunkLineStatusAll.Value,
          grab.ChunkCounterValue.Value
        )
        self.metadata.append(metadata)

    except KeyboardInterrupt:
       print('Recording was stopped by user.')
    finally:
      self.cam_array.StopGrabbing()
      self.cam_array.Close()
      cv2.destroyAllWindows()

if __name__ == '__main__':
   context = Context()
   context.run_loop()