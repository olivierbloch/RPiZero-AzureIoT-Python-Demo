import os
import asyncio
import concurrent.futures
import uuid
import time
import threading
import functools
import json
import base64
import hmac
import hashlib
import random

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import Message
from azure.iot.device import MethodResponse

#======================================
# To switch from PC to RPi, switch commented/uncommented sections below
# Note that on the real device we like to set the connection in an environment variable to not carry it around in code 
#======================================
from blinkt import set_pixel, set_brightness, show, clear
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
#======================================
# conn_str = 'ENTER_CONNECTION_STRING_HERE'
# def set_pixel(i, r, g, b):
#     time.sleep(0.1)
# def set_brightness(b):
#     time.sleep(0.1)
# def show():
#     time.sleep(0.1)
# def clear():
#     time.sleep(0.1)
#======================================

class Led:
    status=False
    blink=False
    r=255
    g=255
    b=255

    def __init__(self, r=255, g=255, b=255):
        self.status = False
        self.blink = False
        self.r = r
        self.g = g
        self.b = b

    def set_color(self, r,g,b):
        self.r = r
        self.g = g
        self.b = b

    def set_status(self, status):
        self.status = status

    def set_blink(self, yesno):
        self.blink = yesno

# list of leds
class Led_Manager:
    leds = []
    scroll_leds = False

    def __init__(self):
        for i in range(8):
            self.leds.append(Led())
        set_brightness(0.1)


    def set_all_leds_color(self, r, g, b):
        for i in range(8):
            self.leds[i].set_color(r, g, b)

    def set_led(self, i, status, r, g, b, blk=False):
        self.leds[i].set_color(r, g, b)
        self.leds[i].set_status(status)
        self.leds[i].blink=blk

    def set_all_leds_off(self):
        self.scroll_leds = False
        for i in range(8):
            self.leds[i].set_status(False)

    def start_scrolling(self):
        self.scroll_leds = True

    def stop_scrolling(self):
        self.scroll_leds = False

    async def scroll_leds_task(self):
        while True:
            if (self.scroll_leds):
                print("Scrolling leds")
                for i in range(8):
                    clear()
                    set_pixel(i, self.leds[i].r, self.leds[i].g, self.leds[i].b)
                    show()
                    await asyncio.sleep(0.05)
                clear()
                show()
            else:
                await asyncio.sleep(.5)

    async def update_leds_task(self):
        new_status = locals()
        for i in range(8):
            new_status[i] = self.leds[i].status
        while True:
            if (not self.scroll_leds):
                clear()
                for i in range(8):
                    if (self.leds[i].blink and self.leds[i].status):
                        new_status[i] = not new_status[i]
                    else:
                        new_status[i]=self.leds[i].status
                    if (new_status[i]):
                        set_pixel(i, self.leds[i].r, self.leds[i].g, self.leds[i].b)
                show()
            await asyncio.sleep(.5)


def printjson(obj):
    parsed = json.dumps(obj)
    loaded = json.loads(parsed)
    print(json.dumps(loaded, indent=2, sort_keys=True))

led_manager = Led_Manager()
message_index = 1

async def main():
    # Thread pool Executor to execute async fucntions in sync task
#    pool = concurrent.futures.ThreadPoolExecutor()

    # Extract device id from connection string
    conn_str_obj = dict(item.split('=', 1) for item in conn_str.split(';'))
    device_id = conn_str_obj["DeviceId"]

    # The client object is used to interact with your Azure IoT hub.
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)
    
    # Function for sending message
    async def send_test_message(i):
            global led_manager
            global message_index
            print("sending message #" + str(message_index))
            body_dict = {}
            body_dict['Weather'] = {}
            body_dict['Weather']['Temperature'] = random.randrange(65, 75, 1)
            body_dict['Weather']['Humidity'] = random.randrange(40, 60, 1)
            body_dict['Location']='28.424911, -81.468962'
            body_json = json.dumps(body_dict)
            print(body_json)
            msg = Message(body_json)
            msg.message_id = uuid.uuid4()
            msg.correlation_id = "correlation-1234"
            msg.custom_properties["Alert"] = "no"
            msg.contentEncoding="utf-8",
            msg.contentType="application/json",
            await device_client.send_message(msg)
            print('Message #' + str(message_index) + ' sent' )
            led_manager.set_led(i, 'On', 0, 255, 0, True)
            message_index=message_index+1

    async def send_alert_message():
            print("Sending alert from device " + device_id)
            body_dict = {}
            body_dict['Weather'] = {}
            body_dict['Weather']['Temperature'] = random.randrange(76, 80, 1)
            body_dict['Weather']['Humidity'] = random.randrange(40, 60, 1)
            body_dict['Location']='28.424911, -81.468962'
            body_json = json.dumps(body_dict)
            print(body_json)
            msg = Message(body_json)
            msg.message_id = uuid.uuid4()
            msg.correlation_id = "correlation-1234"
            msg.custom_properties["Alert"] = "yes"
            msg.contentEncoding="utf-8",
            msg.contentType="application/json",
            await device_client.send_message(msg)
            print("Done sending alert message")


    # update the reported properties
    async def update_device_twin(device_client, led_manager):
        reported_properties = {}
        for i in range (8):
            key='led'+ str(i+1) +'_status' 
            reported_properties[key] = led_manager.leds[i].status
            key='led'+ str(i+1) +'_blink' 
            reported_properties[key] = led_manager.leds[i].blink
            key='led'+ str(i+1) +'_r' 
            reported_properties[key] = led_manager.leds[i].r
            key='led'+ str(i+1) +'_g' 
            reported_properties[key] = led_manager.leds[i].g
            key='led'+ str(i+1) +'_b' 
            reported_properties[key] = led_manager.leds[i].b
        await device_client.patch_twin_reported_properties(reported_properties)
        print("Updated Device Twin's reported properties:")
        printjson(reported_properties)

    # define behavior for receiving a twin patch
    async def twin_patch_listener(device_client, led_manager):
        while True:
            patch = await device_client.receive_twin_desired_properties_patch()  # blocking call
            print("Received new device twin's desired properties:")
            printjson(patch)
            for i in range (8):
                led_status = led_manager.leds[i].status
                led_blink = led_manager.leds[i].blink
                led_r = led_manager.leds[i].r
                led_g = led_manager.leds[i].g
                led_b = led_manager.leds[i].b
                key='led'+ str(i+1) +'_status'
                if key in patch:
                    led_status = patch[key]
                key='led'+ str(i+1) +'_blink'
                if key in patch:
                    led_blink = patch[key]
                key='led'+ str(i+1) +'_r' 
                if key in patch:
                    led_r = patch[key]
                key='led'+ str(i+1) +'_g' 
                if key in patch:
                    led_g = patch[key]
                key='led'+ str(i+1) +'_b' 
                if key in patch:
                    led_b = patch[key]
                led_manager.set_led(i, led_status, led_r, led_g, led_b, led_blink)
            await update_device_twin(device_client, led_manager)

    async def direct_methods_listener(device_client, led_manager):
        while True:
            method_request = (
                await device_client.receive_method_request()
            )  # Wait for unknown method calls
            
            # Check which method was involked
            if (method_request.name == "TurnLedsOff"):
                # Turn all leds off
                led_manager.set_all_leds_off()
                response_payload = {"result": True, "data": "Leds are all off"}  # set response payload
                response_status = 200  # set return status code
                print("Executed method " + method_request.name)

            elif (method_request.name == "ScrollLeds"):
                # Set leds colors and start scrolling
                led_manager.set_all_leds_off()
                led_manager.set_all_leds_color(255, 255, 255)
                led_manager.start_scrolling()
                response_payload = {"result": True, "data": "Leds are now scrolling"}  # set response payload
                response_status = 200  # set return status code
                print("Executed method " + method_request.name)

            else:
                # Respond
                response_payload = {"result": True, "data": "unknown method"}  # set response payload
                response_status = 200  # set return status code
                print("Executed unknown method: " + method_request.name)

            method_response = MethodResponse.create_from_method_request(
                method_request, response_status, response_payload
            )
            await device_client.send_method_response(method_response)  # send response

    # Schedule tasks for Methods and twins updates
    led_listeners = asyncio.gather(
        led_manager.scroll_leds_task(),
        led_manager.update_leds_task()
        )

    # Connect the client.
    print("Connecting to Azure IoT...")
    led_manager.set_all_leds_color(0, 0, 255)
    led_manager.start_scrolling()
    await device_client.connect()
    print("Device is connected to Azure IoT")
    led_manager.set_all_leds_off()

    # Update Device Twin reported properties
    await update_device_twin(device_client, led_manager)
    
    # Schedule tasks for Methods and twins updates
    iothub_listeners = asyncio.gather(
        direct_methods_listener(device_client, led_manager),
        twin_patch_listener(device_client, led_manager)
        )

    # define behavior for halting the application
    def stdin_listener():
        pool = concurrent.futures.ThreadPoolExecutor()
        while True:
            selection = input("Commands: \n   Q: quit\n   S: Send batch of messages in sequence\n   A: Send an alert message\n")
            if selection == "Q" or selection == "q":
                print("Quitting...")
                break
            elif selection == "S" or selection =="s":
                # send 8 messages one after the other with a sleep
                for i in range (8):
                    result = pool.submit(asyncio.run, send_test_message(i)).result()
                    time.sleep(1)
                result = pool.submit(asyncio.run, update_device_twin(device_client, led_manager)).result() # Update reported properties
            elif selection == "A" or selection =="a":
                # send an alert message
                result = pool.submit(asyncio.run, send_alert_message()).result()

    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)
  
    # Wait for user to indicate they are done listening for messages
    await user_finished

    # Cancel listening
    led_listeners.cancel()
    iothub_listeners.cancel()

    # finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

# If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
