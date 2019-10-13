#!/bin/bash
# UniPi driver setup
# Modified for EEE3096S - MCP7940x
if [ "$EUID" -ne 0 ]
    then echo "This script must be run as root"
    exit
fi

echo Backup files
cp /boot/config.txt /boot/config.txt.bak
echo Enabling I2C bus...
if ! grep -q  '^dtparam=i2c_arm=on' /boot/config.txt
    then echo  'dtparam=i2c_arm=on' >> /boot/config.txt
fi

if ! grep -q  '^dtparam=i2c_baudrate=400000' /boot/config.txt
    then echo  'dtparam=i2c_baudrate=400000' >> /boot/config.txt
fi
echo Enabling the RTC chip...
if ! grep -q  '^dtoverlay=i2c-rtc,mcp7940x' /boot/config.txt
    then echo  'dtoverlay=i2c-rtc,mcp7940x' >> /boot/config.txt
fi

echo Getting i2c development tools
apt-get install -y i2c-tools
if ! grep -q  '^i2c-dev' /etc/modules
    then echo  'i2c-dev' >> /etc/modules
fi

echo Removing fake-hwclock...
apt-get purge -y fake-hwclock
update-rc.d -f fake-hwclock remove
apt-get autoremove -y

sed -i  '/^if \[ -e \/run\/systemd\/system/,/^fi/s/^/#/' /lib/udev/hwclock-set

echo  ' '
echo  'UniPi installed.'
echo  ' '
echo  '!!! REBOOT IS REQUIRED !!!'
echo  ' ' 
read -p "Is it OK to reboot now? [y/N] " -n 1 -r
echo  ' '
if [[ $REPLY =~ ^[Yy]$ ]]
then
  reboot 
else
  echo  'Reboot to finish configuring drivers'
fi
echo  ' '