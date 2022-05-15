#!/bin/bash
while true
do
	sleep 30
	sudo python3 /home/pi/stay-watch-reciever/uuid_scanner.py -t 180
	sudo hciconfig hci0 down
	sudo hciconfig hci0 up
done

