sudo pip3 install schedule
sudo pip3 install bluepy

sudo cp /home/pi/stay-watch-reciever/autostart.service  /etc/systemd/system/

sudo chown root:root /etc/systemd/system/autostart.service
sudo chmod 644 /etc/systemd/system/autostart.service
sudo systemctl enable /etc/systemd/system/autostart.service
sudo reboot

