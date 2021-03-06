# -*- coding: utf-8 -*-
import validators
from stringsFunctions import StaticAnswers


def deduplicate(reply):
	"""
	list deduplication method
	:param list reply: list containing non unique items
	:return: list containing unique items
	"""
	reply_dedup = list()
	for item in reply:
		if item not in reply_dedup:
			reply_dedup.append(item)

	return reply_dedup


def validate(keyword, target):
	"""
	validation method to reduce malformed querys and unnecessary connection attempts
	:param keyword: used keyword
	:param target: provided target
	:return: true if valid
	"""
	# if keyword in domain_keywords list
	if keyword in StaticAnswers().keys('domain_keywords'):
		# if target is a domain / email return True
		if validators.domain(target) or validators.email(target):
			return True

	# check if keyword is in number_keyword list
	elif keyword in StaticAnswers().keys('number_keywords'):
		# prevent AttributeError if target is NoneType
		if target is not None:
			# if target only consists of digits return True
			return target.isdigit()

	# if keyword is in no_arg_keywords list return True
	elif keyword in StaticAnswers().keys("no_arg_keywords"):
		return True

	# if the target could not be validated until this return False
	return False


#
class HandleError:
	"""
	simple XMPP error / exception class formating the error condition
	"""
	def __init__(self, error, key, target):
		# init all necessary variables
		self.text = error.text
		self.condition = error.condition
		self.key = key
		self.target = target

	def report(self):
		# return the formatted result string to the user
		text = "%s. %s %s resulted in: %s" % (self.text, self.key, self.target, self.condition)

		return text
