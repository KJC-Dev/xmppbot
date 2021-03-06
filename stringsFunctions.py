# -*- coding: utf-8 -*-
from random import randint


class StaticAnswers:
	"""
	collection of callable static/ semi-static strings
	"""
	def __init__(self, nick=""):
		self.nickname = nick
		self.helpfile = {
			'help':		'!help -- display this text',
			'version':	'!version domain.tld  -- receive XMPP server version',
			'uptime':	'!uptime domain.tld -- receive XMPP server uptime',
			'contact':	'!contact domain.tld -- receive XMPP server contact address info',
			'xep': 		'!xep XEP Number -- recieve information about the specified XEP'
		}
		self.possible_answers = {
			'1': 'I heard that, %s.',
			'2': 'I am sorry to hear that %s.',
			'3': '%s did you try turning it off and on again?'
		}
		self.error_messages = {
			'1': 'not reachable',
			'2': 'not a valid target'
		}
		self.keywords = {
			"keywords": ["!help", "!uptime", "!version", "!contact", "!xep"],
			"domain_keywords": ["!uptime", "!version", "!contact"],
			"no_arg_keywords": ["!help"],
			"number_keywords": ["!xep"]
		}

	def keys(self, key=""):
		# if specific keyword in referenced return that
		if key in self.keywords.keys():
			return self.keywords[key]

		# in any other case return the whole dict
		return self.keywords["keywords"]

	def gen_help(self):
		helpdoc = "\n".join(['%s' % value for (_, value) in self.helpfile.items()])
		return helpdoc

	def gen_answer(self):
		possible_answers = self.possible_answers
		return possible_answers[str(randint(1, possible_answers.__len__()))] % self.nickname

	def error(self,code):
		try:
			text = self.error_messages[str(code)]
		except KeyError:
			return 'unknown error'
		return text
