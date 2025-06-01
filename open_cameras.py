from pypylon import pylon
import sys

try:
    # Create an instant camera object with the first detected camera device
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

    print("Using camera:", camera.GetDeviceInfo().GetModelName())

    # Open the camera
    camera.Open()

    # Start grabbing 5 frames
    camera.StartGrabbingMax(5)

    # Convert image format to something viewable (e.g. for OpenCV)
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_Mono8
    converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    while camera.IsGrabbing():
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            # Convert to NumPy array
            image = converter.Convert(grabResult)
            img = image.GetArray()
            print(f"Captured frame of shape {img.shape}")
        else:
            print("Failed to grab frame.")

        grabResult.Release()

    camera.Close()
    print("Camera test completed successfully.")

except Exception as e:
    print("Error:", e)
    sys.exit(1)
