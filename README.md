# sync_master

~~~
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
git clone https://github.com/cobaal/sync_master.git
sudo chmod +x ~/catkin_ws/src/sync_master/nodes/sync_master_node
cd ~/catkin_ws
catkin_make

rospack depends1 symc_master
rosrun sync_master sync_master_node
~~~
