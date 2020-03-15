# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

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
import sys
import random

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import Message
from azure.iot.device import MethodResponse

from blinkt import set_pixel, set_brightness, show, clear

def derive_device_key(device_id, group_symmetric_key):
    """
    The unique device ID and the group master key should be encoded into "utf-8"
    After this the encoded group master key must be used to compute an HMAC-SHA256 of the encoded registration ID.
    Finally the result must be converted into Base64 format.
    The device key is the "utf-8" decoding of the above result.
    """
    message = device_id.encode("utf-8")
    signing_key = base64.b64decode(group_symmetric_key.encode("utf-8"))
    signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
    device_key_encoded = base64.b64encode(signed_hmac.digest())
    return device_key_encoded.decode("utf-8")

#======================================
# To switch from PC to RPi, switch commented/un-commented sections below 
#======================================
from blinkt import set_pixel, set_brightness, show, clear
provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_DEVICE_ID")
group_symmetric_key = os.getenv("PROVISIONING_MASTER_SYMMETRIC_KEY")
symmetric_key = derive_device_key( 
    device_id=registration_id,
    group_symmetric_key=group_symmetric_key,
)
#======================================
# provisioning_host = 'global.azure-devices-provisioning.net'
# id_scope = '<IDScope>'
# registration_id = '<DeviceId>'
# group_symmetric_key = '<Provisioning-master-key>'
# symmetric_key = derive_device_key( 
#     device_id=registration_id,
#     group_symmetric_key=group_symmetric_key,
# )
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

async def main():
        
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

    # Thread pool Executor to execute async functions in sync task
    # pool = concurrent.futures.ThreadPoolExecutor()

    device_id = registration_id
    print("Connecting device " + device_id)

    # Connect the client.
    print("Provisioning device to Azure IoT...")
    led_manager.set_all_leds_color(0, 255, 0)
    led_manager.start_scrolling()

    # registration using DPS
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=symmetric_key
    )

    registration_result = await provisioning_device_client.register()

    led_manager.set_all_leds_off()

    if registration_result.status == "assigned":
        print("Device successfully registered. Creating device client")
        # Create device client from the above result
        device_client = IoTHubDeviceClient.create_from_symmetric_key(
            symmetric_key=symmetric_key,
            hostname=registration_result.registration_state.assigned_hub,
            device_id=registration_result.registration_state.device_id,
        )
    else:
        led_manager.set_led(0, true, 255, 0, 0, true)
        print("Provisioning of the device failed.")
        sys.exit()

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
            print("To control the leds from Azure IoT, you can send the following commands through Direct Methods: TurnLedsOff, ScrollLeds")
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