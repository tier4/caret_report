#!/bin/bash -e

# Add user and group: start
USER_ID=$(id -u)
GROUP_ID=$(id -g)

if [ x"$GROUP_ID" != x"0" ]; then
    groupadd -g $GROUP_ID $USER_NAME
fi

if [ x"$USER_ID" != x"0" ]; then
    useradd -d /home/$USER_NAME -m -s /bin/bash -u $USER_ID -g $GROUP_ID $USER_NAME
fi
export HOME=/home/$USER_NAME

sudo chmod u-s /usr/sbin/useradd
sudo chmod u-s /usr/sbin/groupadd
# Add user and group: end

# Add to .bashrc for VSCode
echo "source /opt/ros/humble/setup.bash" >> $HOME/.bashrc
echo "source /ros2_caret_ws/install/local_setup.bash" >> $HOME/.bashrc
echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash" >> $HOME/.bashrc

cd /work
# work_dir="work_"`date +"%Y%m%d_%H%M%S"`
# mkdir $work_dir
# cd $work_dir

exec "$@"
