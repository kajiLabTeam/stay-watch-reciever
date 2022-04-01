sudo pip3 install schedule
sudo nano /etc/systemd/system/autostart.servicen

[Unit]
Description=do something
ConditionPathExists=/home/pi/stay-watch-reciever

[Service]
ExecStart=/home/pi/stay-watch-reciever/newstart.sh
Restart=no
Type=simple

[Install]
WantedBy=multi-user.target

sudo chown root:root /etc/systemd/system/autostart.service
sudo chmod 644 /etc/systemd/system/autostart.service
sudo systemctl enable /etc/systemd/system/autostart.service
sudo reboot


