echo "******************************************"
echo "******************************************"
echo "****                                  ****"
echo "****              MOODE               ****"
echo "****                                  ****"
echo "******************************************"
echo "******************************************"
sudo cp /opt/moOde_OLED/moode-oled.service /etc/systemd/system/
sudo systemctl enable moode-oled.service
echo "might need to add 'sudo systemctl start moode-oled.service'"
echo "******************************************"
echo "***      Successfully Installed        ***"
echo "******************************************"
sleep 5
sudo reboot
