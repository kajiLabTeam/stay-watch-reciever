sudo pip3 install schedule
sudo pip3 install bluepy
sudo pip3 install requests
sudo cp /home/pi/stay-watch-reciever/autostart.service  /etc/systemd/system/

sudo chmod +x /home/pi/stay-watch-reciever/newstart.sh
sudo chown root:root /etc/systemd/system/autostart.service
sudo chmod 644 /etc/systemd/system/autostart.service
sudo systemctl enable /etc/systemd/system/autostart.service
sudo reboot



