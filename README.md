# sync_master

~~~
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
git clone https://github.com/cobaal/sync_master.git
cd ~/catkin_ws
catkin_make

rospack depends1 symc_master
rosrun sync_master sync_master_node
~~~
