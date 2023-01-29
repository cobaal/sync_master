# sync_master

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
[udp, multicast] rosrun sync_master sync_master_node
[tcp, unicast] rosrun sync_master tcp_sync_master_node [option: --root]
~~~

# ERROR
1. IOError: [Errno 13] Permission denied: '~/.ros/log/{NODE NAME}.log'
~~~
rm ~/.ros/log/{NODE NAME}.log
~~~
