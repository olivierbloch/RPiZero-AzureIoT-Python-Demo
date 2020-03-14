# Simple Azure IoT demo with Raspberry Pi Zero W

This repo contains a couple very simple Python scripts showing how to connect a Raspberry Pi Zero W to Azure IoT Hub using the Python SDK.
I have been using a [Pimoroni](https://learn.pimoroni.com/) Rpi Zero W kit with a [Blinkt](https://learn.pimoroni.com/tutorial/sandyj/getting-started-with-blinkt) led strip. 
This sample is based on the ones found in the [IoT Hub Python Device SDK repository](https://github.com/Azure/azure-iot-sdk-python/tree/master/azure-iot-device).

# Setup

## Setup Raspbian on the Raspberry Pi Zero W

To setup the Raspberry Pi Zero W, follow the instructions coming with the board or from [the Sparkfun site](https://learn.sparkfun.com/tutorials/getting-started-with-the-raspberry-pi-zero-wireless/all#installing-the-os). Raspbian Lite should suffice.

## Setup the Blinkt! library

In order to control the leds of the Blinkt! hat, you need to install the Python library following the instructions on the [getting started page](https://learn.pimoroni.com/tutorial/sandyj/getting-started-with-blinkt).

# Connect to Azure IoT Hub

## Create an IoT Hub and a device ID

I highly recommend getting and using the [Azure IoT Explorer](https://docs.microsoft.com/en-us/azure/iot-pnp/howto-install-iot-explorer) tool. On the tool's documentation page you will find all the instructions you need to create a new IoT Hub, create a device identity, then use the Azure IoT Explorer tool to interact with your device (monitor telemetry, interact with the Device Twin, invoke Direct Methods). 

## Get the code sample onto the device and install required libs

Once you have created a new device ID and retrieved its primary connection string, you can will need to copy the file [IoTHubClient.py](./IoTHubClient.py) from this repo onto your device. The simplest way is to use SSH.
In your favorite SSH client, connect to your device

```bash
ssh pi@XXX.XXX.XXX.XXX
```

Once in the ssh session, you can create a folder or just create the file at the root using nano

```bash
sudo nano IoTHubClient.py
```

Then copy paste the code from the repo into the new file.

You will need to install required Python libraries:

```bash
pip install azure-iot-device
```

## Set environment variables

The code sample uses environment variables to manage credentials. In an actual production scenario you would want to store these credentials safely in some Hardware Secure Module, but for the sake of the sample, we are simplifying, still NOT putting credentials in the code :-).
Copy the device connection string from the Azure IoT Explorer tool, then use the below command on the device to add a new Environment variable:

```bash
export IOTHUB_DEVICE_CONNECTION_STRING="<deviceconnectionstring>"
```

## Run the sample

Now you are ready to run the sample on the device:

```bash
python IoTHubClient.py
```

# Connect to Azure IoT Central

This one is work in progress, stay tuned!