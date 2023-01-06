#!/usr/bin/env python

import rospy

def main():
	import sync_master.local_state_finder as local_state_finder

	rospy.init_node('sync_master_node')
	my_node_name = str(rospy.get_name())

	state_finder = local_state_finder.StateFinder(my_node_name)
	state_finder.start()
	rospy.spin()
	state_finder.stop()





