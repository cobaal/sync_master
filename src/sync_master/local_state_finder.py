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

			print("\t!" + str(data))

			if data[0] == 'pub':
				## registerPublisher(NODE_NAME, TOPIC_NAME, TOPIC_TYPE, NODE_URI)
				print(self.my_master.registerPublisher(data[1], data[2], data[3], data[4]))

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
		#  CATCHING THE LOCAL NODES (USING URI OF NODES)
		#  NodeInfo class
		#    - node_name
		#    - node_uri
		#    - node_pid
		#    - publishedTopic	: dict[TOPIC_NAME] = TOPIC_TYPE
		#    - subscribedTopic	: dict[TOPIC_NAME] = TOPIC_TYPE
		#    - service
		##
		node_names = rosnode.get_node_names()
		for node_name in node_names:
			node_uri = self._succeed(self.my_master.lookupNode(self.my_node_name, node_name))
			# node_uri = self.my_master.lookupNode(node_name)
			node_pid = -1
			if self.is_local_node(self.my_node_uri, node_uri):
				node_api = xmlrpcclient.ServerProxy(node_uri)	# Useless til now...
				node_pid = self._succeed(node_api.getPid(node_name))
			if not node_name in self.nodes.keys() or self.nodes[node_name].isDuplicated(node_name, node_uri, node_pid) == False:
				print("NEW NODE : " + node_name + "\t" + node_uri)
				self.nodes[node_name] = NodeInfo(node_name, node_uri, node_pid)		
			# else:
			# 	print(node_name + '\t: is duplicated!')	
		
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
		# pub
		for topic_name, pub_nodes in state[0]:
			for pub_node in pub_nodes:
				if self.nodes[pub_node].addPublishedTopics(topic_name, topic_type_list[topic_name]) == 0:
					print("NEW PUB TOPIC! : " + pub_node + "\t" + topic_name + "(" + topic_type_list[topic_name] + ")")
					if self.nodes[pub_node].node_pid != -1 and topic_name != '/rosout' and topic_name != '/rosout_agg':
						data = ['pub', pub_node, topic_name, topic_type_list[topic_name], self.nodes[pub_node].node_uri]
						print("\t(pub)\t" + str(data))
						payload = pickle.dumps(data)
						self.sendMulticastMsg(payload)

		# sub
		for topic_name, sub_nodes in state[1]:
			for sub_node in sub_nodes:
				if self.nodes[sub_node].addSubscribedTopics(topic_name, topic_type_list[topic_name]) == 0:
					print("NEW SUB TOPIC! : " + sub_node + "\t" + topic_name + "(" + topic_type_list[topic_name] + ")")
					if self.nodes[sub_node].node_pid != -1 and topic_name != '/rosout' and topic_name != '/rosout_agg':
						data = ['sub', sub_node, topic_name, topic_type_list[topic_name], self.nodes[sub_node].node_uri]
						print("\t(sub)\t" + str(data))
						payload = pickle.dumps(data)
						self.sendMulticastMsg(payload)

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

	def sendMulticastMsg(self, payload):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.MCAST_TTL)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
		sock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))