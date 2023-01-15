#!/usr/bin/env python

import rospy
try:
	import xmlrpclib as xmlrpcclient  # python 2 compatibility
except ImportError:
	import xmlrpc.client as xmlrpcclient

class NodeInfo(object):
	def __init__(self, node_name, node_uri):
		self._node_name = node_name
		self._node_uri = node_uri
		self._node_pid = -1
		self._isLocal = False
		self._isFiltered = False
		self._publishedTopics = {}
		self._subscribedTopics = {}
		self._services = {}


	@property
	def node_name(self):
		return self._node_name

	@property
	def node_uri(self):
		return self._node_uri

	@property
	def node_pid(self):
		return self._node_pid

	@node_pid.setter
	def node_pid(self, node_pid):
		self._node_pid = node_pid

	@property
	def isLocal(self):
		return self._isLocal

	@isLocal.setter
	def isLocal(self, isLocal):
		self._isLocal = isLocal

	@property
	def isFiltered(self):
		return self._isFiltered

	@isFiltered.setter
	def isFiltered(self, isFiltered):
		self._isFiltered = isFiltered

	@property
	def publishedTopics(self):
		return self._publishedTopics

	@property
	def subscribedTopics(self):
		return self._subscribedTopics

	def addPublishedTopics(self, topic_name, topic_type):
		self._publishedTopics[topic_name] = topic_type

	def isDuplicatedPublishedTopics(self, topic_name):
		if topic_name in self._publishedTopics.keys():
			return True
		else:
			return False

	def addSubscribedTopics(self, topic_name, topic_type):
		self._subscribedTopics[topic_name] = topic_type

	def isDuplicatedSubscribedTopics(self, topic_name):
		if topic_name in self._subscribedTopics.keys():
			return True
		else:
			return False

	@property
	def services(self):
		return self._services

	def addService(self, service_name, service_uri):
		self._services[service_name] = service_uri

	def isDuplicatedService(self, service_name):
		if service_name in self._services.keys():
			return True
		else:
			return False

	def isDuplicated(self, node_name, node_uri):
		if self._node_name == node_name and self._node_uri == node_uri:
			return True
		else:
			return False				
