import serial
import time

ser = None

def connect(com_port, baudrate=9600, timeout=1):
    global ser
    if ser is not None and ser.is_open:
        ser.close()
    ser = serial.Serial(com_port, baudrate, timeout=timeout)
    time.sleep(2)
    return ser.is_open

def sendSerial(data):
    if ser is None or not ser.is_open:
        raise RuntimeError("Serial port is not connected.")
    ser.write(data.encode('utf-8'))

def readLine():
    if ser is None or not ser.is_open:
        return None
    if ser.in_waiting > 0:
        return ser.readline().decode('utf-8').rstrip()
    return None

def close():
    global ser
    if ser is not None and ser.is_open:
        ser.close()
