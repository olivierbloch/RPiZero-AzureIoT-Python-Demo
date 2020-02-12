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

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import Message
from azure.iot.device import MethodResponse

from blinkt import set_pixel, set_brightness, show, clear

messages_to_send = 8

class Led:
    status='Off'
    r=255
    g=255
    b=255

    def __init__(self, r=255, g=255, b=255):
        self.status = 'Off'
        self.r = r
        self.g = g
        self.b = b

    def set_color(self, r,g,b):
        self.r = r
        self.g = g
        self.b = b

    def set_status(self, status):
        self.status = status

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

    def set_led(self, i, status, r, g, b):
        self.leds[i].set_color(r, g, b)
        self.leds[i].set_status(status)
        self.update_leds()

    def set_all_leds_off(self):
        self.scroll_leds = False
        for i in range(8):
            self.leds[i].set_status('Off')
        self.update_leds()

    def update_leds(self):
        clear()
        for i in range(8):
            if (self.leds[i].status=='On'):
                set_pixel(i, self.leds[i].r, self.leds[i].g, self.leds[i].b)
        show()

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

led_manager = Led_Manager()

async def main():
    # Thread pool Executor to execute async fucntions in sync task
    pool = concurrent.futures.ThreadPoolExecutor()

    # registration using connection string
    # The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
#    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    # The client object is used to interact with your Azure IoT hub.
#    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

    # registration using DPS
    provisioning_host = os.getenv("PROVISIONING_HOST")
    id_scope = os.getenv("PROVISIONING_IDSCOPE")
    device_id = os.getenv("PROVISIONING_DEVICE_ID")
    master_symmetric_key = os.getenv("PROVISIONING_MASTER_SYMMETRIC_KEY")

    def derive_device_key(device_id):
        """
        The unique device ID and the group master key should be encoded into "utf-8"
        After this the encoded group master key must be used to compute an HMAC-SHA256 of the encoded registration ID.
        Finally the result must be converted into Base64 format.
        The device key is the "utf-8" decoding of the above result.
        """
        message = device_id.encode("utf-8")
        signing_key = base64.b64decode(master_symmetric_key.encode("utf-8"))
        signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
        device_key_encoded = base64.b64encode(signed_hmac.digest())
        return device_key_encoded.decode("utf-8")

    async def register_device(device_id):
        provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=provisioning_host,
            registration_id=device_id,
            id_scope=id_scope,
            symmetric_key=derive_device_key(device_id),
        )
        return await provisioning_device_client.register()

    results = await asyncio.gather(
        register_device(device_id)
    )
    registration_result = results[0]
    print("The complete state of registration result is")
    print(registration_result.registration_state)

    
    # Function for sending message
    async def send_test_message(i):
            global led_manager
            print("sending message #" + str(i+1))
            msg = Message("test wind speed " + str(i+1))
            msg.message_id = uuid.uuid4()
            msg.correlation_id = "correlation-1234"
            msg.custom_properties["tornado-warning"] = "yes"
            await device_client.send_message(msg)
            print("done sending message #" + str(i+1))
            led_manager.set_led(i, 'On', 0, 255, 0)

    # update the reported properties
    async def update_device_twin(device_client, led_manager):
        reported_properties = {}
        for i in range (8):
            key='led'+ str(i+1) +'_status' 
            reported_properties[key] = led_manager.leds[i].status
            key='led'+ str(i+1) +'_r' 
            reported_properties[key] = led_manager.leds[i].r
            key='led'+ str(i+1) +'_g' 
            reported_properties[key] = led_manager.leds[i].g
            key='led'+ str(i+1) +'_b' 
            reported_properties[key] = led_manager.leds[i].b
        print("Setting reported properties to {}".format(reported_properties))
        await device_client.patch_twin_reported_properties(reported_properties)

    # define behavior for receiving a twin patch
    async def twin_patch_listener(device_client, led_manager):
        while True:
            patch = await device_client.receive_twin_desired_properties_patch()  # blocking call
            print("the data in the desired properties patch was: {}".format(patch))
            for i in range (8):
                led_status = led_manager.leds[i].status
                led_r = led_manager.leds[i].r
                led_g = led_manager.leds[i].g
                led_b = led_manager.leds[i].b
                key='led'+ str(i+1) +'_status'
                if key in patch:
                    led_status = patch[key]
                key='led'+ str(i+1) +'_r' 
                if key in patch:
                    led_r = patch[key]
                key='led'+ str(i+1) +'_g' 
                if key in patch:
                    led_g = patch[key]
                key='led'+ str(i+1) +'_b' 
                if key in patch:
                    led_b = patch[key]
                led_manager.set_led(i, led_status, led_r, led_g, led_b)
            led_manager.update_leds()   
            await update_device_twin(device_client, led_manager)

    # define behavior for handling methods
    async def turn_leds_off_listener(device_client, led_manager):
        while True:
            method_request = await device_client.receive_method_request(
                "TurnLedsOff"
            )  # Wait for TurnLedsOff calls

            led_manager.set_all_leds_off()
            payload = {"result": True, "data": "All Leds were turned off"}  # set response payload
            status = 200  # set return status code
            print("executed TurnLedsOff")
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            await device_client.send_method_response(method_response)  # send response

    async def scroll_leds_listener(device_client, led_manager):
        while True:
            method_request = await device_client.receive_method_request(
                "ScrollLeds"
            )  # Wait for ScrollLeds calls
            # Set leds colors
            led_manager.set_all_leds_off()
            led_manager.set_all_leds_color(255, 255, 255)
            led_manager.start_scrolling()
            
            # Respond to IoT Hub
            payload = {"result": True, "data": "Leds now scrolling"}  # set response payload
            status = 200  # set return status code
            print("executed ScrollLeds")
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            await device_client.send_method_response(method_response)  # send response

    # Schedule tasks for Methods and twins updates
    led_listeners = asyncio.gather(
        led_manager.scroll_leds_task()
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
        turn_leds_off_listener(device_client, led_manager),
        scroll_leds_listener(device_client, led_manager),
        twin_patch_listener(device_client, led_manager)
        )

    # define behavior for halting the application
    def stdin_listener():
        pool = concurrent.futures.ThreadPoolExecutor()
        while True:
            selection = input("Commands: \n   Q: quit\n   S: Send batch of messages in sequence\n")
            if selection == "Q" or selection == "q":
                print("Quitting...")
                break
            elif selection == "S" or selection =="s":
                # send 8 messages one after the other with a sleep
                for i in range (8):
                    result = pool.submit(asyncio.run, send_test_message(i)).result()
                    time.sleep(1)

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
