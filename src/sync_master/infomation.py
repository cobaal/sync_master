#!/usr/bin/env python

import rospy
try:
	import xmlrpclib as xmlrpcclient  # python 2 compatibility
except ImportError:
	import xmlrpc.client as xmlrpcclient

class NodeInfo(object):
	def __init__(self, node_name, node_uri, node_pid):
		self._node_name = node_name
		self._node_uri = node_uri
		self._node_pid = node_pid
		self._publishedTopics = {}
		self._subscribedTopics = {}
		self._services = []


	@property
	def node_name(self):
		return self._node_name

	@property
	def node_uri(self):
		return self._node_uri

	@property
	def node_pid(self):
		return self._node_pid

	@property
	def publishedTopics(self):
		return self._publishedTopics

	@property
	def subscribedTopics(self):
		return self._subscribedTopics

	def addPublishedTopics(self, topic_name, topic_type):
		if topic_name in self._publishedTopics.keys() and topic_type in self._publishedTopics.values():
			return -1
		else:
			self._publishedTopics[topic_name] = topic_type
			return 0

	def addSubscribedTopics(self, topic_name, topic_type):
		if topic_name in self._subscribedTopics.keys() and topic_type in self._subscribedTopics.values():
			return -1
		else:
			self._subscribedTopics[topic_name] = topic_type
			return 0

	@property
	def services(self):
		return self._services

	@services.setter
	def services(self, name):
		try:
			if isinstance(name, list):
				del self._services
				self._services = name
			else:
				self._services.index(name)
		except ValueError:
			self._services.append(name)

	def isDuplicated(self, node_name, node_uri, node_pid):
		if self._node_name == node_name and self._node_uri == node_uri and self._node_pid == node_pid:
			return True
		else:
			return False				

# class TopicInfo(object):
# 	def __init__(self, topic_name, topic_type):
# 		self._topic_name = topic_name
# 		self._topic_type = topic_type

# 	@property
# 	def topic_name(self):
# 		return self._topic_name

# 	@property
# 	def topic_type(self):
# 		return self._topic_type