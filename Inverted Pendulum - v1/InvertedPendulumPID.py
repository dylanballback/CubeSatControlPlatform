import time
import board
import adafruit_lsm9ds1
import odrive
import math
import threading
import can 
import struct
from simple_pid import PID
from InertialMeasurementUnit import InertialMeasurementUnit

#Set motor to v = velocity
def set_vel():
    global running
    while running:
        velocity = pid(IMU1.angle_x)
        bus.send(can.Message(arbitration_id=(node_id << 5 | 0x0d), data=struct.pack('<ff', float(velocity), 0.0), is_extended_id=False))
        time.sleep(0.01)

def read_angle(imu_obj):
    global running
    while running:
        imu_obj.get_euler_angles()
        time.sleep(0.01)

def get_pos_vel(imu_obj):
    while running:
        for msg in bus:
            if msg.arbitration_id == (node_id << 5 | 0x09):
                pos, vel = struct.unpack('<ff', bytes(msg.data))
                print(f"Roll: {imu_obj.angle_x:.2f} degrees, vel: {vel:.3f} [turns/s]")


#CAN initialization
node_id = 0
bus = can.interface.Bus("can0", bustype="socketcan")

while not (bus.recv(timeout=0) is None): pass
bus.send(can.Message(arbitration_id=(node_id << 5 | 0x07), data=struct.pack('<I', 8), is_extended_id=False))

start_time = time.time()
timeout = 10  # seconds

for msg in bus:
    if time.time() - start_time > timeout:
        print("Timeout waiting for the expected CAN message.")
        break

    if msg.arbitration_id == (node_id << 5 | 0x01):
        error, state, result, traj_done = struct.unpack('<IBBB', bytes(msg.data[:7]))
        if state == 8:
            break

#Initialize instance of InertialMeasurementUnit
IMU1 = InertialMeasurementUnit()

#Setup PID controller
set_point = 0 #Pendulum upright
pid = PID(-1, 0, 0, setpoint=set_point)
pid.output_limits = (-30, 30) #RPS bounds on motor

#Global variables
running = True
odrive_error_detected = False

# Threads
imu_thread = threading.Thread(target=read_angle, args=(IMU1,))
motor_thread = threading.Thread(target=set_vel)
pos_thread = threading.Thread(target=get_pos_vel, args=(IMU1,))

imu_thread.start()
motor_thread.start()
pos_thread.start()

try:
    while True:
        time.sleep(0.001)

except KeyboardInterrupt:
    running = False
    bus.shutdown()
    print("\nProgram terminated gracefully.")