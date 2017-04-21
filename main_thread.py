## !/usr/bin/env python

from flask import *
from flask_socketio import SocketIO
from flask_socketio import send, emit
from gpiozero import *
from time import sleep
import Adafruit_DHT, psutil
from threading import Thread
import threading, signal

# pin 4 for DHT22 sensor data pin
GPIO_PIN = 4
SENSOR = Adafruit_DHT.AM2302

# Create flask app, SocketIO object
app = Flask(__name__)
socketio = SocketIO(app)

# Create  object
led = OutputDevice(21)
aircond = OutputDevice(20)
# get CPU temperature
# add "threshold" argument in the instantiation to set our limit between cool and hot
temp = CPUTemperature(min_temp=0, max_temp=100,threshold=50)

@socketio.on('setaircond')
def set_aircond(state):
    if state == 1:
        aircond.on()
    if state == 0:
        aircond.off()

    print("Aircond status: {}".format(aircond.value))

@socketio.on('setled')
def set_led(state):
    if state == 1:
        led.on()
    if state == 0:
        led.off()
    print("Led status: {}".format(led.value))

@app.route("/")
def index():
    return render_template('index.html')

class AM2302(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

    def run(self):
        print('AM2302 Temp+Humid Sensor Startup: Thread #%s started' % self.ident)
        while not self.shutdown_flag.is_set():
            # ... Job code here ...
            hum,tmp = Adafruit_DHT.read_retry(SENSOR,GPIO_PIN)
            print("DATA from AM2302: t:{:.2f} h:{:.2f}".format(tmp,hum))

            socketio.emit('temp', int(tmp))
            socketio.emit('hum', int(hum))

            sleep(2)
        # ... Clean shutdown code here ...
        print('')
        print('AM2302 Temp+Humid SensorShutdown : Thread #%s stopped' % self.ident)


class CPU_usage(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

    def run(self):
        print('CPU_usage Startup: Thread #%s started' % self.ident)
        while not self.shutdown_flag.is_set():
            # ... Job code here ...
            cpu = psutil.cpu_percent()
            print("DATA from cpu: process:{:.2f} ".format(cpu))

            socketio.emit('cpu', float(cpu))
            sleep(2)
        # ... Clean shutdown code here ...
        print('')
        print('CPU_usage Shutdown : Thread #%s stopped' % self.ident)

class CPU_temp(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

    def run(self):
        print('CPU_temp Startup: Thread #%s started' % self.ident)
        while not self.shutdown_flag.is_set():
            # ... Job code here ...
            temp_val = temp.value * 100
            print("DATA from cpu_temp: cputmp:{:.2f} ".format(temp_val))
            socketio.emit('cputemp', int(temp_val))
            socketio.emit('cputempthres', temp.is_active)
            sleep(2)
        # ... Clean shutdown code here ...
        print('')
        print('CPU_temp Shutdown : Thread #%s stopped' % self.ident)

class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass


def service_shutdown(signum, frame):
    print('Caught signal %d' % signum)
    raise ServiceExit


def main():

    # Register the signal handlers
    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)

    print('Starting main program')

    # Start the job threads
    try:
        temp_thread = AM2302()
        cpu_usage_thread = CPU_usage()
        cpu_temp_thread = CPU_temp()
        temp_thread.start()
        cpu_usage_thread.start()
        cpu_temp_thread.start()

        socketio.run(app,host='0.0.0.0', debug=True)

        # Keep the main thread running, otherwise signals are ignored.
        while True:
            sleep(0.1)

    except ServiceExit:

        # Terminate the running threads.
        # Set the shutdown flag on each thread to trigger a clean shutdown of each thread.
        temp_thread.shutdown_flag.set()
        cpu_usage_thread.shutdown_flag.set()
        cpu_temp_thread.shutdown_flag.set()
        # Wait for the threads to close...
        temp_thread.join()
        cpu_usage_thread.join()
        cpu_temp_thread.join()

    print('\n')
    print('Cleanly Exiting main program')
    print('Mission Accomplished')

if __name__ == "__main__" :
    main()
