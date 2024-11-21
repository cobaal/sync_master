# Install

~~~
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
git clone https://github.com/cobaal/sync_master.git
sudo chmod +x ~/catkin_ws/src/sync_master/nodes/sync_master_node
sudo chmod +x ~/catkin_ws/src/sync_master/nodes/tcp_sync_master_node
cd ~/catkin_ws
catkin_make

source ~/catkin_ws/devel/setup.bash
source ~/catkin_ws/devel/setup.sh

rospack depends1 sync_master
~~~

# ERROR
1. IOError: [Errno 13] Permission denied: '~/.ros/log/{NODE NAME}.log'
~~~
rm ~/.ros/log/{NODE NAME}.log
~~~
2. error: [Errno 19] No such device (multicast socket)
~~~
ip route add default via {ip} dev {iface}
~~~

# How to use (TCP: default)
Com A (root)
~~~
echo 'export ROS_HOSTNAME={IP_of_this_com_A}' >> ~/.bashrc
echo 'export ROS_MASTER_URI=http://{IP_of_this_com_A}:11311' >> ~/.bashrc
source ~/.bashrc

(new terminal) roscore
(new terminal) rosrun sync_master tcp_sync_master_node --root
~~~

Com B (non-root)
~~~
echo 'export ROS_HOSTNAME={IP_of_this_com_B}' >> ~/.bashrc
echo 'export ROS_MASTER_URI=http://{IP_of_this_com_B}:11311' >> ~/.bashrc
source ~/.bashrc

(new terminal) roscore
(new terminal) rosrun sync_master tcp_sync_master_node
~~~
There must be exactly one root. It doesn't matter if non-root execute first.

# How to use (UDP)
Com A 
~~~
echo 'export ROS_HOSTNAME={IP_of_this_com_A}' >> ~/.bashrc
echo 'export ROS_MASTER_URI=http://{IP_of_this_com_A}:11311' >> ~/.bashrc
source ~/.bashrc

(new terminal) roscore
(new terminal) rosrun sync_master sync_master_node
~~~

Com B
~~~
echo 'export ROS_HOSTNAME={IP_of_this_com_B}' >> ~/.bashrc
echo 'export ROS_MASTER_URI=http://{IP_of_this_com_B}:11311' >> ~/.bashrc
source ~/.bashrc

(new terminal) roscore
(new terminal) rosrun sync_master sync_master_node
~~~
UDP manner has no root.
