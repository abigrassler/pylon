from pypylon import pylon
import cv2
import os
from datetime import datetime

# Create output folder
recording_dir = r"D:\abi_data\raw_data\setup\test_cameras\camA"
os.makedirs(recording_dir, exist_ok=True)

# Generate filename with timestamp
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
video_filename = os.path.join(recording_dir, f"{timestamp}.mp4")

# Connect to camera
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()
camera.StartGrabbing()

# Set up image format converter
converter = pylon.ImageFormatConverter()
converter.OutputPixelFormat = pylon.PixelType_BGR8packed
converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

# Grab one frame to get dimensions
grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
image = converter.Convert(grabResult)
frame = image.GetArray()
height, width, _ = frame.shape
grabResult.Release()

# Set up video writer
fps = 20.0  # You can adjust this to match your camera
fourcc = cv2.VideoWriter_fourcc(*'XVID')
video_writer = cv2.VideoWriter(video_filename, fourcc, fps, (width, height))

print("Recording started. Press 'q' in the preview window to stop.")

# Main loop
while camera.IsGrabbing():
    grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
    if grabResult.GrabSucceeded():
        image = converter.Convert(grabResult)
        frame = image.GetArray()

        # Write and show frame
        video_writer.write(frame)
        cv2.imshow("Live Preview", frame)

        # Exit on 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    grabResult.Release()

# Cleanup
camera.StopGrabbing()
camera.Close()
video_writer.release()
cv2.destroyAllWindows()

print(f"Recording saved to {video_filename}")
