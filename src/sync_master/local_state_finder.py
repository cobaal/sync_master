#!/usr/bin/env python

# import rospy
try:
	import xmlrpclib as xmlrpcclient  # python 2 compatibility
except ImportError:
	import xmlrpc.client as xmlrpcclient

import time
import threading

import rosgraph
import rosnode

import pickle
import socket
import struct

from .infomation import NodeInfo

class StateFinder(object):
	def __init__(self, my_node_name):
		self.my_node_name = my_node_name
		self.timer_interval = 1
		self.node_list = []
		self.nodes = {}

		self.MCAST_GRP = '224.1.1.1'
		self.MCAST_PORT = 5007
		self.MCAST_TTL = 1

		# print(my_node_name)

	def msg_receive_thread(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		sock.bind((self.MCAST_GRP, self.MCAST_PORT))
		mreq = struct.pack("4sl", socket.inet_aton(self.MCAST_GRP), socket.INADDR_ANY)

		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

		while True:
			payload = sock.recv(1024)
			data = pickle.loads(payload)

			# print("* received msg: " + str(data))

			if data[0] == 'pub':
				## registerPublisher(NODE_NAME, TOPIC_NAME, TOPIC_TYPE, NODE_URI)
				print(self.my_master.registerPublisher(data[1], data[2], data[3], data[4]))
			elif data[0] == 'upub':
				## unregisterPublisher(NODE_NAME, TOPIC_NAME, NODE_URI)
				print(self.my_master.unregisterPublisher(data[1], data[2], data[3]))
			elif data[0] == 'sub':
				## registerSubscriber(NODE_NAME, TOPIC_NAME, TOPIC_TYPE, NODE_URI)
				print(self.my_master.registerSubscriber(data[1], data[2], data[3], data[4]))
			elif data[0] == 'usub':
				## unregisterSubscriber(NODE_NAME, TOPIC_NAME, NODE_URI)
				print(self.my_master.unregisterSubscriber(data[1], data[2], data[3]))
			

	def state_finder_thread(self):
		##
		#  GETTING MASTER API OF THIS NODE (I.E., SYNC_MASTER NODE'S MASTER OBJECT)
		#  GETTING THIS NODE URI
		##
		self.my_master = xmlrpcclient.ServerProxy("http://localhost:11311")
		self.my_node_uri = self._succeed(self.my_master.lookupNode(self.my_node_name, self.my_node_name))
		# self.my_master = rosgraph.Master("")
		# self.my_node_uri = self.my_master.lookupNode(self.my_node_name)

		##
		#  GETTING LIST OF NODES IN THIS MASTER INCLUDING OTHER NODES OBTAINED FROM OTHER MASTERS
		#  CATCHING THE CHANGES IN NODE (NEW/REMOVE)
		#  NodeInfo class
		#    - node_name
		#    - node_uri
		#    - node_pid
		#    - isLocal			: False (default)
		#    - isFiltered		: False (default)
		#    - publishedTopics	: dict[TOPIC_NAME] = TOPIC_TYPE
		#    - subscribedTopics	: dict[TOPIC_NAME] = TOPIC_TYPE
		#    - service
		##
		node_names = rosnode.get_node_names()
		new_nodes = set(node_names) - set(self.node_list)

		# ADD NEW NODES
		for node_name in new_nodes:
			# ADD NEW NODE
			node_uri = self._succeed(self.my_master.lookupNode(self.my_node_name, node_name))
			self.nodes[node_name] = NodeInfo(node_name, node_uri)

			# FILTERING
			self.nodes[node_name].isLocal = self.is_local_node(self.my_node_uri, node_uri)
			self.nodes[node_name].isFiltered = self.is_filtered_node(node_name)

			print("[ NEW         ]\t*NAME: " + node_name + "\n[ NODE        ]\t*URI : " + node_uri + "\n\t\t*isLocal: " + str(self.nodes[node_name].isLocal) + "\n\t\t*isFiltered: " + str(self.nodes[node_name].isFiltered) + "\n")

		# DELETE REMOVED NODES
		removed_nodes = set(self.node_list) - set(node_names)
		for node_name in removed_nodes:
			node_uri = self.nodes[node_name].node_uri
			print("[ REMOVED     ]\t*NAME: " + node_name + "\n[ NODE        ]\t*URI : " + node_uri + "\n")

			# DELETE REMOVED TOPICS AND SEND MESSAGE
			if self.nodes[node_name].isLocal == True:
				# UNPUBLISH
				for topic_name in self.nodes[node_name].publishedTopics.keys():
					print("[     REMOVED ]\t*NODE:  " + node_name + " (Publisher)\n[       TOPIC ]\t*TOPIC: " + topic_name + "\n")
					data = ['upub', node_name, topic_name, self.nodes[node_name].node_uri]
					payload = pickle.dumps(data)
					self.sendMulticastMsg(payload)
				# UNSUBSCRIBE
				for topic_name in self.nodes[node_name].subscribedTopics.keys():
					print("[     REMOVED ]\t*NODE:  " + node_name + " (Subscriber)\n[       TOPIC ]\t*TOPIC: " + topic_name + "\n")
					data = ['usub', node_name, topic_name, self.nodes[node_name].node_uri]
					payload = pickle.dumps(data)
					self.sendMulticastMsg(payload)
			
			# DELETE NODE
			del self.nodes[node_name]

		# SAVE NODE LIST
		self.node_list = node_names
			
		##
		#  GETTING TOPIC NAME NAD TYPE LIST OF THIS DEVICE
		#  [[TOPIC_NAME, TOPIC_TYPE], ...] FROM getTopicTypes() 
		#  TOPIC TYPE DICT : DICT[TOPIC_NAME] = TOPIC_TYPE
		##
		topic_type_list = {}
		topic_types = self._succeed(self.my_master.getTopicTypes(self.my_node_name))
		# topic_types = self.my_master.getTopicTypes()
		for topic_name, topic_type in topic_types:
			topic_type_list[topic_name] = topic_type

		##
		#  GETTING STATE OF THIS LOCAL MASTER FROM getSystemState()
		#  [0] : PUBLISHED TOPIC	[[TOPIC_NAME, [PUBLISHER_1, PUBLISHER_2, ...]], ...]
		#  [1] : SUBSCRIBED TOPIC	[[TOPIC_NAME, [SUBSCRIBER_1, SUBSCRIBER_2, ...]], ...]
		##
		state = self._succeed(self.my_master.getSystemState(self.my_node_name))
		# state = self.my_master.getSystemState()

		# STATE OF PUBLISHERS
		for topic_name, pub_nodes in state[0]:
			for pub_node in pub_nodes:
				# CHECK THE OVERLAP TOPICS
				if self.nodes[pub_node].addPublishedTopics(topic_name, topic_type_list[topic_name]) == 0:
					print("[         NEW ]\t*NODE:  " + pub_node + " (Publisher)\n[       TOPIC ]\t*TOPIC: " + topic_name + " (type: " + topic_type_list[topic_name] + ")\n")
					# SEND MESSAGE
					if self.nodes[pub_node].isLocal == True and self.nodes[pub_node].isFiltered == False:
						data = ['pub', pub_node, topic_name, topic_type_list[topic_name], self.nodes[pub_node].node_uri]
						payload = pickle.dumps(data)
						self.sendMulticastMsg(payload)

		# STATE OF SUBSCRIBERS
		for topic_name, sub_nodes in state[1]:
			for sub_node in sub_nodes:
				# CHECK THE OVERLAP TOPICS
				if self.nodes[sub_node].addSubscribedTopics(topic_name, topic_type_list[topic_name]) == 0:
					print("[         NEW ]\t*NODE:  " + sub_node + " (Subscriber)\n[       TOPIC ]\t*TOPIC: " + topic_name + " (type: " + topic_type_list[topic_name] + ")\n")
					# SEND MESSAGE
					if self.nodes[sub_node].isLocal == True and self.nodes[sub_node].isFiltered == False:
						data = ['sub', sub_node, topic_name, topic_type_list[topic_name], self.nodes[sub_node].node_uri]
						payload = pickle.dumps(data)
						self.sendMulticastMsg(payload)

		# TODO : Find the unpub and unsub topics of which the nodes are still alived.

		# print("")
		# for node in self.nodes.values():
		# 	print(node.node_name)
		# 	print("\t" + node.node_uri + " (PID:" + str(node.node_pid) + ")")
		# 	print("\tPUB : " + str(node.publishedTopics))
		# 	print("\tSUB : " + str(node.subscribedTopics))
		# 	print("")

		# code, message, topicTypes = self.my_master.getTopicTypes(self.my_node_name)
		# topicTypesDict = {}
		# for topic, type in topicTypes:
		# 	topicTypesDict[topic] = type
		# print(topicTypesDict)
		# print('=============================')
		# code, message, state = self.my_master.getSystemState(self.my_node_name)
		# print(state[0])
		# print('=============================')
		# print(state[1])
		# print('=============================')
		# print(state[2])
		# print('')

		
		# print(self.my_node_name)

		self.t0 = threading.Timer(self.timer_interval, self.state_finder_thread)
		self.t0.daemon = True
		self.t0.start()

	def start(self):
		self.t0 = threading.Thread(target=self.state_finder_thread)
		self.t1 = threading.Thread(target=self.msg_receive_thread)
		self.t0.daemon = True
		self.t1.daemon = True
		self.t0.start()
		self.t1.start()

	def stop(self):
		print('\n\n * Terminated.')

	def _succeed(self, args):
		code, msg, val = args
		if code != 1:
			raise Exception("Error: %s" % msg)
		return val

	def is_local_node(self, my_node_uri, target_node_uri):
		m_http, m_ip, m_port = my_node_uri.split(':')
		t_http, t_ip, t_port = target_node_uri.split(':')
		
		if m_ip == t_ip:
			return True
		else:
			return False

	def is_filtered_node(self, target_node_name):
		filter_node_list = [self.my_node_name, '/rosout', 'rosout_agg']

		if target_node_name in filter_node_list:
			return True
		else:
			return False

	def sendMulticastMsg(self, payload):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.MCAST_TTL)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
		sock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))