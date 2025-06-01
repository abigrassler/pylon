import cv2
import enum
import itertools
import os
import pandas as pd

from pypylon import pylon, genicam
from datetime import datetime, timedelta

class CameraState(enum.Enum):
   Idle = enum.auto()
   Recording = enum.auto()



class Context:
  def __init__(self):
    # Discover and connect to camera
    tlf = pylon.TlFactory.GetInstance()
    self.cam = pylon.InstantCamera(tlf.CreateFirstDevice())
    self.cam.Open()
    self.camera_state = CameraState.Idle
    self.trigger_line = 3
    self.trigger_line_id = f'Line{self.trigger_line}'
    self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
    self.frame_rate = 200.0
    self.sampling_rate = 1.0 / self.frame_rate
    self.output_resolution = (800, 600)

    # Load the default camera configuration 
    self.cam.UserSetSelector.Value = "Default"
    self.cam.UserSetLoad.Execute()

    # Select recording settings
    self.camera_dir = os.path.join('D', os.path.sep, 'abi_data', 'raw_data', 'setup', 'test_cameras', 'camA')
    os.makedirs(self.camera_dir, exist_ok=True) 

    # Set the chunks you want (metadata). Here we want to sample IO lines on each framestart trigger 
    chunks = ["LineStatusAll", "Timestamp", "CounterValue"]
    self.cam.ChunkModeActive.SetValue(True) #attach metadata to each image 
    for chunk in chunks:
      self.cam.ChunkSelector.SetValue(chunk) #metadata about IO line status for each image (state of TTL pulse)
      if chunk == "CounterValue":
        self.cam.CounterSelector.SetValue("Counter1")
        self.cam.CounterEventSource.SetValue("FrameStart")
      self.cam.ChunkEnable.SetValue(True) #activates chunk you are interested in (LineStatus)

      if not self.cam.ChunkEnable.GetValue():
        print(f'Tried to enable chunk {chunk}, but it reported as disabled')

    # Set image quality and format settings 
    self.cam.Height.SetValue(600)
    self.cam.Width.SetValue(800)
    self.cam.ExposureTime.SetValue(3000)
    self.cam.AcquisitionFrameRateEnable.SetValue(True)
    self.cam.AcquisitionFrameRate.SetValue(200)
    self.cam.GainAuto.SetValue("Continuous")

    # Setup the trigger/acquisition controls 
    self.cam.TriggerSelector.SetValue("FrameStart")
    self.cam.TriggerActivation.SetValue("RisingEdge")
    self.cam.TriggerSource.SetValue(self.trigger_line_id)
    self.cam.TriggerMode.SetValue("On")

    # Create an image format converter
    self.converter = pylon.ImageFormatConverter()
    self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed  # For OpenCV (color)
    self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    # We'll start a new video whenever the beam is broken, so just make a placeh
    self.video_writer: cv2.VideoWriter = None

    self.metadata = []
    self.video_timestamp = None
    self.frame_timestamp = 0
    self.max_frame_delta = timedelta(seconds=self.sampling_rate * 1.5)

  def run_loop(self):
    self.cam.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByUser) # Starts a steady stream of images, provides 1 frame at a time when triggered 
    
    try:
      while True:
        grab = self.cam.RetrieveResult(pylon.waitForever, pylon.TimeoutHandling_Return)

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
          file_name = f'camA_{self.video_timestamp}.avi'
          file_path = os.path.join(self.camera_dir, file_name)

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
      self.cam.StopGrabbing()
      self.cam.Close()
      cv2.destroyAllWindows()

if __name__ == '__main__':
   context = Context()
   context.run_loop()

