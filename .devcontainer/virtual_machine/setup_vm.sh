#!/bin/bash
set -e

#Installing ROS
sudo -s
mkdir -p /workspace
chown mivia /workspace
ln -s /workspace /home/mivia && chown mivia /home/mivia
echo "mivia ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers #Disable sudo password for user mivia
su mivia
sudo apt update && sudo apt install –y git
cd /workspace/.devcontainer/windows_mac
bash ros2_humble_install.bash
bash ros2-tools.bash

sudo -s
cd /workspace/.devcontainer/windows_mac

apt update && apt install -y iputils-ping net-tools nano gedit x11-apps mlocate python3-pip curl wget sudo ffmpeg git-lfs htop

pip install -U pip

apt update && apt install -y ros-humble-rviz2 \
                            ros-humble-rqt-common-plugins \
                            ros-humble-rqt-tf-tree \
                            ros-humble-rqt-image-view \
                            ros-humble-tf-transformations \
                            ros-humble-diagnostic-updater  \
                            ros-humble-image-transport-plugins

# #Transformers
pip install --ignore-installed  datasets \
                                torchcodec \
                                'transformers[torch]'==4.56.1 bitsandbytes==0.47 accelerate \
                                huggingface_hub[cli]

# #Installing RASA
cd /opt/
apt install -y python3.10-venv
python3 -m venv venv --system-site-packages && \
source venv/bin/activate && \
pip install rasa==3.6.21 rasa[spacy] && \
python -m spacy download en_core_web_md && \
python -m spacy download it_core_news_md && \
ln -s /opt/venv/bin/activate /usr/local/bin/activate_rasa_env && \
chmod +x /usr/local/bin/activate_rasa_env
deactivate

pip install pyOpenssl

#Fix Pepper 230
cd /usr/local/bin
apt update && apt install -y sshpass && \
wget https://github.com/gdesimone97/cogrob_pepper_nodes/releases/download/fix-pepper/fix_pepper && \
chmod +x fix_pepper


#NAOqi
cd /workspace/.devcontainer/windows_mac
cp ../install_qi.bash /tmp/
bash /tmp/install_qi.bash

# #Audio libs
apt update && apt install -y portaudio19-dev alsa-base alsa-utils
pip install sounddevice soundfile librosa pyaudio

# #Respeaker
python3 -m pip install pyusb==1.0.2 'click>=8.1.3' pixel-ring==0.1.0
python3 -m pip install -U --ignore-installed transforms3d

# #Cleanup
apt-get clean \
&& rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
&& rm -rf /root/.cache

# #Python utils
pip install -U httpx pyOpenssl scipy==1.15.3

# #ROS utils
apt update && apt install -y ros-humble-angles

# #NO MOVE!
pip install numpy==1.26.3 'setuptools<80,>=30.3.0'

cat <<EOF >> /etc/profile

export PATH=$PATH:/home/mivia/.local/bin

# ROS
export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID=0
 
#PYTHON
export PYTHONPATH=/workspace/demo_utils:$PYTHONPATH

EOF

usermod -aG dialout mivia
cat <<EOF >> /etc/udev/rules.d/99-usb-dialout.rules

SUBSYSTEM=="usb", ATTR{idVendor}=="2886", ATTR{idProduct}=="0018", GROUP="dialout", MODE="0660"

EOF

reboot
