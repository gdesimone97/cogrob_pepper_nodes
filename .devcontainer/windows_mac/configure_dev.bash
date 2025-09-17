sudo -s
usermod -aG dialout mivia
cat <<EOF >> /etc/udev/rules.d/99-usb-dialout.rules

SUBSYSTEM=="usb", ATTR{idVendor}=="2886", ATTR{idProduct}=="0018", GROUP="dialout", MODE="0660"

EOF