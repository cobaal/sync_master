#!/usr/bin/env python

# import rospy
try:
	import xmlrpclib as xmlrpcclient  # python 2 compatibility
except ImportError:
	import xmlrpc.client as xmlrpcclient

# import time
import threading

# import rosgraph
# import rosnode

import pickle
import socket
import struct

from .infomation import NodeInfo

class StateFinder(object):
	def __init__(self, my_node_name):
		self._lock = threading.Lock()

		self.my_node_name = my_node_name
		self.timer_interval = 1
		self.node_list = []
		self.nodes = {}

		# FOR MULTICAST SOCKET
		self.MCAST_GRP = '224.1.1.1'
		self.MCAST_PORT = 5007
		self.MCAST_TTL = 1

		self.mtsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.mtsock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.MCAST_TTL)
		self.mtsock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)

		# FOR UNICAST SOCKET
		self.UCAST_PORT = 3001

		'''
		* GETTING MASTER API OF THIS NODE (I.E., SYNC_MASTER NODE'S MASTER OBJECT)
		* GETTING THIS NODE URI
		'''
		self._lock.acquire()
		self.my_master = xmlrpcclient.ServerProxy("http://localhost:11311")
		self.my_node_uri = self._succeed(self.my_master.lookupNode(self.my_node_name, self.my_node_name))
		# self.my_master = rosgraph.Master("")
		# self.my_node_uri = self.my_master.lookupNode(self.my_node_name)
		self._lock.release()

		self.local_ip = self.my_node_uri.split('/')[2].split(':')[0]

	def msg_receive_thread(self):
		self.mrsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.mrsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		self.mrsock.bind((self.MCAST_GRP, self.MCAST_PORT))
		mreq = struct.pack("4sl", socket.inet_aton(self.MCAST_GRP), socket.INADDR_ANY)

		self.mrsock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

		while True:
			try:
				payload = self.mrsock.recv(1024)
				data = pickle.loads(payload)
			except Exception as e:
				print('** Exception (rx multicast, pickle) : ' + e + '\n')

			if data[0] == 'pub':
				## registerPublisher(NODE_NAME, TOPIC_NAME, TOPIC_TYPE, NODE_URI)
				self._lock.acquire()
				print(self.my_master.registerPublisher(data[1], data[2], data[3], data[4]))
				self._lock.release()
			elif data[0] == 'upub':
				## unregisterPublisher(NODE_NAME, TOPIC_NAME, NODE_URI)
				self._lock.acquire()
				print(self.my_master.unregisterPublisher(data[1], data[2], data[3]))
				self._lock.release()
			elif data[0] == 'sub':
				## registerSubscriber(NODE_NAME, TOPIC_NAME, TOPIC_TYPE, NODE_URI)
				self._lock.acquire()
				print(self.my_master.registerSubscriber(data[1], data[2], data[3], data[4]))
				self._lock.release()
			elif data[0] == 'usub':
				## unregisterSubscriber(NODE_NAME, TOPIC_NAME, NODE_URI)
				self._lock.acquire()
				print(self.my_master.unregisterSubscriber(data[1], data[2], data[3]))
				self._lock.release()
			elif data[0] == 'service':
				## registerService(NODE_NAME, SERVICE_NAME, SERVICE_URI, NODE_URI)
				self._lock.acquire()
				print(self.my_master.registerService(data[1], data[2], data[3], data[4]))
				self._lock.release()
			elif data[0] == 'uservice':
				## unregisterService(NODE_NAME, SERVICE_NAME, SERVICE_URI)
				self._lock.acquire()
				print(self.my_master.unregisterService(data[1], data[2], data[3]))
				self._lock.release()
			elif data[0] == 'req':
				## RESPONSE : STATE OF LOCAL MASTER
				msg = []
				for __node in self.nodes.values():
					if __node.isFiltered == False:
						## PUB
						for pub_name in __node.publishedTopics.keys():
							msg.append(['pub', __node.node_name, pub_name, __node.publishedTopics[pub_name], __node.node_uri])
						## SUB
						for sub_name in __node.subscribedTopics.keys():
							msg.append(['sub', __node.node_name, sub_name, __node.subscribedTopics[sub_name], __node.node_uri])
						## SVC
						for svc_name in __node.services.keys():
							msg.append(['service', __node.node_name, svc_name, __node.services[svc_name], __node.node_uri])

				tdata = ['res', msg]
				tpayload = pickle.dumps(tdata)

				utsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				try:
					utsock.connect((data[1], self.UCAST_PORT))
					utsock.send(tpayload)
				except Exception as e:
					print('** Exception (tx tcp unicast) : ' + e + '\n')

				utsock.close()
			
	def sync_adjacent_master(self):
		# MULTICASTING SYNC REQ SIGNAL
		data = ['req', self.local_ip]
		payload = pickle.dumps(data)
		self.mtsock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))

		# RECEIVE UNICAST MESSAGE - ADJACENT MASTER'S URI
		ursock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		ursock.bind((self.local_ip, self.UCAST_PORT))
		ursock.listen(1)

		crsock, addr = ursock.accept()
		print("[ SYNC ] RECEIVING SYNC MSG FROM " + addr[0] + "...\n")

		try:
			_payload = crsock.recv(10240)
			_data = pickle.loads(_payload)
		except Exception as e:
			print('** Exception (rx tcp unicast, pickle) : ' + e + '\n')

		if _data[0] == 'res':
			for msg in _data[1]:
				if msg[0] == 'pub':
					## registerPublisher(NODE_NAME, TOPIC_NAME, TOPIC_TYPE, NODE_URI)
					self._lock.acquire()
					print(self.my_master.registerPublisher(msg[1], msg[2], msg[3], msg[4]))
					self._lock.release()
				elif msg[0] == 'sub':
					## registerSubscriber(NODE_NAME, TOPIC_NAME, TOPIC_TYPE, NODE_URI)
					self._lock.acquire()
					print(self.my_master.registerSubscriber(msg[1], msg[2], msg[3], msg[4]))
					self._lock.release()
				elif msg[0] == 'service':
					## registerService(NODE_NAME, SERVICE_NAME, SERVICE_URI, NODE_URI)
					self._lock.acquire()
					print(self.my_master.registerService(msg[1], msg[2], msg[3], msg[4]))
					self._lock.release()

		crsock.close()
		ursock.close()

	def state_finder_thread(self):
		'''
		* GETTING LIST OF NODES IN THIS MASTER INCLUDING OTHER NODES OBTAINED FROM OTHER MASTERS
		* CATCHING THE CHANGES IN NODE (NEW/REMOVE)
		:NodeInfo class
			- node_name
			- node_uri
			- node_pid
			- isLocal			: False (default)
			- isFiltered		: False (default)
			- publishedTopics	: dict[TOPIC_NAME] = TOPIC_TYPE
			- subscribedTopics	: dict[TOPIC_NAME] = TOPIC_TYPE
			- service			: dict[SERVICE_NAME] = SERVICE_URI
		'''

		'''
		* GETTING STATE OF THIS LOCAL MASTER FROM getSystemState()
		* [0] : PUBLISHED TOPIC		[[TOPIC_NAME, [PUBLISHER_1, PUBLISHER_2, ...]], ...]
		* [1] : SUBSCRIBED TOPIC	[[TOPIC_NAME, [SUBSCRIBER_1, SUBSCRIBER_2, ...]], ...]
		* [2] : SERVICE				[[SERVICE_NAME, [NODE_1, NODE_2, ...]], ...]
		'''
		self._lock.acquire()
		state = self._succeed(self.my_master.getSystemState(self.my_node_name))
		# state = self.my_master.getSystemState()
		self._lock.release()
		
		_nodes = []
		for s in state:
			for feature_name, set_of_nodes in s:
				_nodes.extend(set_of_nodes)
		node_names = list(set(_nodes))
		# node_names = rosnode.get_node_names()

		new_nodes = set(node_names) - set(self.node_list)

		# ADD NEW NODES
		for node_name in new_nodes:
			# ADD NEW NODE
			self._lock.acquire()
			node_uri = self._succeed(self.my_master.lookupNode(self.my_node_name, node_name))
			self._lock.release()
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

			# DELETE REMOVED PUB/SUB TOPICS, AND SERVICES. SEND MESSAGE
			if self.nodes[node_name].isLocal == True and self.nodes[node_name].isFiltered == False:
				# UNPUBLISH
				for topic_name in self.nodes[node_name].publishedTopics.keys():
					print("[     REMOVED ]\t*NODE:  " + node_name + " (Publisher)\n[       TOPIC ]\t*TOPIC: " + topic_name + "\n")
					data = ['upub', node_name, topic_name, self.nodes[node_name].node_uri]
					payload = pickle.dumps(data)
					self.mtsock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))
				# UNSUBSCRIBE
				for topic_name in self.nodes[node_name].subscribedTopics.keys():
					print("[     REMOVED ]\t*NODE:  " + node_name + " (Subscriber)\n[       TOPIC ]\t*TOPIC: " + topic_name + "\n")
					data = ['usub', node_name, topic_name, self.nodes[node_name].node_uri]
					payload = pickle.dumps(data)
					self.mtsock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))
				# UNSERVICE
				for service_name in self.nodes[node_name].services.keys():
					print("[   REMOVED   ]\t*NODE:    " + node_name + " \n[   SERVICE   ]\t*SERVICE: " + service_name + "\n")
					data = ['uservice', node_name, service_name, self.nodes[node_name].services[service_name]]
					payload = pickle.dumps(data)
					self.mtsock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))
			
			# DELETE NODE
			del self.nodes[node_name]

		# SAVE NODE LIST
		self.node_list = node_names

		# STATE OF PUBLISHERS
		for topic_name, pub_nodes in state[0]:
			for pub_node in pub_nodes:
				# CHECK THE OVERLAP PUB TOPICS
				if self.nodes[pub_node].isDuplicatedPublishedTopics(topic_name) == False:
					topic_type = self.getTopicType(topic_name)
					self.nodes[pub_node].addPublishedTopics(topic_name, topic_type)
					print("[         NEW ]\t*NODE:  " + pub_node + " (Publisher)\n[       TOPIC ]\t*TOPIC: " + topic_name + " (type: " + topic_type + ")\n")
					# SEND MESSAGE
					if self.nodes[pub_node].isLocal == True and self.nodes[pub_node].isFiltered == False:
						data = ['pub', pub_node, topic_name, topic_type, self.nodes[pub_node].node_uri]
						payload = pickle.dumps(data)
						self.mtsock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))

		# STATE OF SUBSCRIBERS
		for topic_name, sub_nodes in state[1]:
			for sub_node in sub_nodes:
				# CHECK THE OVERLAP SUB TOPICS
				if self.nodes[sub_node].isDuplicatedSubscribedTopics(topic_name) == False:
					topic_type = self.getTopicType(topic_name)
					self.nodes[sub_node].addSubscribedTopics(topic_name, topic_type)
					print("[         NEW ]\t*NODE:  " + sub_node + " (Subscriber)\n[       TOPIC ]\t*TOPIC: " + topic_name + " (type: " + topic_type + ")\n")
					# SEND MESSAGE
					if self.nodes[sub_node].isLocal == True and self.nodes[sub_node].isFiltered == False:
						data = ['sub', sub_node, topic_name, topic_type, self.nodes[sub_node].node_uri]
						payload = pickle.dumps(data)
						self.mtsock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))

		# TODO : Find the unpub and unsub topics of which the nodes are still alived.

		# STATE OF SERVICES
		for service_name, service_nodes in state[2]:
			for service_node in service_nodes:
				# CHECK THE OVERLAP SERVICES
				if self.nodes[service_node].isDuplicatedService(service_name) == False:
					self._lock.acquire()
					service_uri = self._succeed(self.my_master.lookupService(self.my_node_name, service_name))
					self._lock.release()
					self.nodes[service_node].addService(service_name, service_uri)
					print("[     NEW     ]\t*NODE:    " + service_node + "\n[   SERVICE   ]\t*SERVICE: " + service_name + "\n\t\t (" + service_uri + ")\n")
					# SEND MESSAGE
					if self.nodes[service_node].isLocal == True and self.nodes[service_node].isFiltered == False:
						data = ['service', service_node, service_name, service_uri, self.nodes[service_node].node_uri]
						payload = pickle.dumps(data)
						self.mtsock.sendto(payload, (self.MCAST_GRP, self.MCAST_PORT))
						
		# pub_nodes = {}
		# for topic_name, nodes in state[0]:
		# 	pub_nodes[topic_name] = nodes

		# # NEW PUB TOPICS
		# new_pub_topics = set(pub_nodes.keys()) - set(self.pubs.keys())
		# for topic_name in new_pub_topics:
		# 	for pub_node in pub_nodes.values():
		# 		print("[ tests    NEW ]\t*NODE:  " + pub_node + " (Publisher)\n[       TOPIC ]\t*TOPIC: " + topic_name + " (type: " + topic_type_list[topic_name] + ")\n")

		# # REMOVED PUB TOPICS
		# removed_pub_topics = set(self.pubs.keys()) - set(pub_nodes.keys())
		# print(removed_pub_topics)

		# for topic in set(pub_nodes.keys()) & set(self.pubs.keys()):
		# 	# NEW PUBLISHERS
		# 	new_publishers = set(self.pubs[topic]) - set(pub_nodes[topic])

		# 	# REMOVED PUBLISHERS
		# 	removed_publishers = set(pub_nodes[topic])- set(self.pubs[topic])

		# 	print(new_publishers)
		# 	print(removed_publishers)
			

		# # SAVE PUB TOPICS
		# self.pubs = pub_nodes

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
		self.t2 = threading.Thread(target=self.sync_adjacent_master)
		self.t0.daemon = True
		self.t1.daemon = True
		self.t2.daemon = True
		self.t0.start()
		self.t1.start()
		self.t2.start()

	def stop(self):
		print('\n\n * Terminated.')

		self.mtsock.close()
		self.mrsock.close()

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

	def getTopicType(self, topic_name):
		'''
		* GETTING TOPIC NAME NAD TYPE LIST OF THIS DEVICE
		* [[TOPIC_NAME, TOPIC_TYPE], ...] FROM getTopicTypes() 
		* TOPIC TYPE DICT : DICT[TOPIC_NAME] = TOPIC_TYPE
		'''
		topic_type_list = {}
		self._lock.acquire()
		topic_types = self._succeed(self.my_master.getTopicTypes(self.my_node_name))
		# topic_types = self.my_master.getTopicTypes()
		self._lock.release()

		for _name, _type in topic_types:
			topic_type_list[_name] = _type

		return topic_type_list[topic_name]