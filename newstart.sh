#!/bin/bash
while true
do

	sleep 10
	##5回繰り返す
	sudo python3 /home/pi/stay-watch-reciever/deleteDB.py
	for i in 1 2 3 4 5
	do
		sudo python3 /home/pi/stay-watch-reciever/uuid_scanner.py -t 60
		sleep 10
	done
	sudo python3 /home/pi/stay-watch-reciever/post_data.py

	sudo hciconfig hci0 down
	sudo hciconfig hci0 up
done



