echo "******************************************"
echo "******************************************"
echo "****                                  ****"
echo "****              MOODE               ****"
echo "****                                  ****"
echo "******************************************"
echo "******************************************"
echo "the below rc.local method doesn't work"
echo "use /etc/systemd/system instead"
sudo sed -i "`wc -l < /etc/rc.local`i\\sudo python3 /opt/moOde_OLED/moOde_OLED.py &\\" /etc/rc.local
sudo cp /opt/moOde_OLED/moode-oled.service /etc/systemd/system/
sudo systemctl enable moode-oled.service
echo "******************************************"
echo "***      Successfully Installed        ***"
echo "******************************************"
sleep 5
sudo reboot
