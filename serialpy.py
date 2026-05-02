import serial
import time

ser = None
_last_cmd = None
_last_sent_ts = 0.0


def is_connected():
    return ser is not None and ser.is_open


def connect(port, baudrate=9600, timeout=1):
    global ser
    if not port:
        raise ValueError('COM port is required.')

    port = port.strip().upper()
    if not port.startswith('COM'):
        port = f'COM{port}'

    if is_connected():
        ser.close()

    ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
    time.sleep(2)
    return port


def send(cmd, dedupe_window_s=0.2):
    global _last_cmd, _last_sent_ts
    if not is_connected():
        raise RuntimeError('Serial not connected. Click Connect serial first.')

    now = time.monotonic()
    # Drop accidental rapid duplicates (double-click, event repeat, etc.).
    if cmd == _last_cmd and (now - _last_sent_ts) < dedupe_window_s:
        return False

    message = f'{cmd}\n'.encode('utf-8')
    ser.write(message)
    ser.flush()
    _last_cmd = cmd
    _last_sent_ts = now
    return True


def right():
    send('RIGHT')


def left():
    send('LEFT')


def center():
    send('CENTER')


def close():
    global ser, _last_cmd, _last_sent_ts
    if is_connected():
        ser.close()
    ser = None
    _last_cmd = None
    _last_sent_ts = 0.0
