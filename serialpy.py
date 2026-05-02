import serial
import time

ser = serial.Serial('COM5', 9600, timeout=1)

time.sleep(2)

def sendSerial(data):
    ser.write(data.encode('utf-8'))

if ser.in_waiting > 0:
    line = ser.readline().decode('utf-8').rstrip()

def close():
    ser.close()