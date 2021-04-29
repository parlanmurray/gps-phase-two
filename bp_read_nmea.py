#! /usr/bin/env python

"""
Requirements:
- pynmea2
- pyserial
- numpy
- matplotlib

http://dangerousprototypes.com/blog/2009/10/09/bus-pirate-raw-bitbang-mode/
http://dangerousprototypes.com/blog/2009/10/19/bus-pirate-binary-uart-mode/
"""

import sys
import io
import time

import serial
import pynmea2
import numpy
import matplotlib.pyplot as plt

# set the following value to your buspirate's port
PORT = "/dev/tty.usbserial-AB0JQY2C"
FILE_FLAG = False
OUTFILE = "logs/" + time.strftime("%Y%m%d-%H%M%S")


def enter_bitbang(conn):
	conn.flushInput()
	for _ in range(20):
		conn.write(b'\x00')
	if not b'BBIO' in conn.read(5):
		cleanup(conn)
		print("failed to enter bitbang")
		sys.exit(1)


def exit_bitbang(conn):
	conn.write(b'\x00')
	conn.write(b'\x0F')


def enter_uart(conn):
	conn.write(b'\x03')
	if not b'ART1' in conn.read(4):
		cleanup(conn)
		print("failed to enter uart")
		sys.exit(1)


def cleanup(conn):
	exit_bitbang(conn)


def configure(conn, byte):
	conn.write(byte)
	if not b'\x01' in conn.read(1):
		cleanup(conn)
		print("failed to configure settings")
		sys.exit(1)

def update_figure(ax, bbox, x, y, img):
	ax.scatter(x, y, zorder=1, alpha=0.2, c='b', s=10)
	ax.imshow(img, zorder=0, extent=bbox, aspect='equal')
	plt.pause(0.001)


conn = serial.Serial(PORT, 115200, timeout=0.1)

# setup
enter_bitbang(conn)
enter_uart(conn)

# configure settings
# set baud rate to 9600
configure(conn, b'\x64')
# set pin output to 3.3v
configure(conn, b'\x90')
# enable power supply
configure(conn, b'\x48')

logfile = open(OUTFILE, "w+")
FILE_FLAG = True

BBox = (2.29367, # long min
	2.29798, # long max
	48.87460, # lat min
	48.87184) # lat max

arc_map = plt.imread("map.png")

fig, ax = plt.subplots(figsize=(8,7))
ax.set_title('GPS coordinates received')
ax.set_xlim(BBox[0],BBox[1])
ax.set_ylim(BBox[2], BBox[3])
plt.ion()
plt.show()

print("setup done")

# start bridge
conn.write(b'\x0f')
conn.read(1)
sio = io.TextIOWrapper(io.BufferedRWPair(conn, conn))

while True:
	try:
		output = sio.read()
		lines = output.split("\n")
		for line in lines:
			if line:
				msg = pynmea2.parse(line)
				if isinstance(msg, pynmea2.GGA) and int(msg.num_sats) != 0:
					print(repr(msg))
				if isinstance(msg, pynmea2.GGA) and int(msg.gps_qual) != 0:
					logfile.write(repr(msg) + "\n")
					update_figure(ax, BBox, float(msg.longitude), float(msg.latitude), arc_map)
	except serial.SerialException as e:
		print("Device error: {}".format(e))
		logfile.write("Device error: {}".format(e) + "\n")
		logfile.close()
		sys.exit(1)
	except pynmea2.ParseError as e:
		print("Parse error: {}".format(e) + "\n")
		logfile.write("Parse error: {}".format(e))
		continue
	except KeyboardInterrupt:
		break

cleanup(conn)
logfile.close()
