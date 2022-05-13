#!/bin/bash
while true
do
	sleep 10
	sudo python3 /home/pi/stay-watch-reciever/uuid_scanner.py -t 60
done

