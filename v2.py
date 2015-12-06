import time
import signal
import re
import threading
from datetime import datetime
import logging
from queue import Queue, Empty

from twx.botapi import TelegramBot, ReplyKeyboardMarkup
from KickassAPI import Search, Latest, User, CATEGORY, ORDER
from api_token import API_TOKEN
__author__ = 'Alex'

logger = logging.Logger("default", 10)  # Debug level


class MessageServer(object):
    def __init__(self):
        self.thread_map = {}
        self.bot = TelegramBot(API_TOKEN)
        self.updates = set(self.bot.get_updates().wait())

    def poll(self):
        while True:
            del_list = []
            for name in self.thread_map:
                thread = self.thread_map[name]
                if thread.finished_event.isSet():
                    del_list.append(name)
            for x in del_list:
                del self.thread_map[x]
            print("<{time}> Waiting....".format(time=datetime.now().time()))
            updates = set(self.bot.get_updates().wait())
            new_updates = updates.difference(self.updates)
            for update in new_updates:
                print("<{time}> Received new message....".format(time=datetime.now().time()))
                user = update.message.sender.id
                if user in self.thread_map:
                    print("<{time}> Dispatching message to thread....".format(time=datetime.now().time()))
                    self.thread_map[user]._add_to_queue(update.message.text)
                else:
                    print("<{time}> Creating new thread....".format(time=datetime.now().time()))
                    user_thread = Worker(user)
                    self.thread_map[user] = user_thread
                    print("<{time}> Dispatching message to thread....".format(time=datetime.now().time()))
                    user_thread._add_to_queue(update.message.text)
                self.updates.add(update)


class Parser(object):
    @classmethod
    def tokenize(cls, message):
        groups = []
        groups_dict = {}
        # Find command
        command_match = re.match(r"^/(?P<command>\w+)\s?.*?", message)
        if command_match:
            groups_dict["type"] = "command"
            groups.append(command_match.group("command"))
            groups_dict["command"] = command_match.group("command")

            arg_match = re.match(r"^/%s\s+(?P<main_arg>(?:\"(?:.*\s?)+\")|\w+)\s?.*?" %
                                 re.escape(command_match.group("command")), message)
            if arg_match:
                arg = arg_match.group("main_arg")
                remove_quotes = re.match("^[\'\"]?(.*?)[\'\"]?$", arg)
                if remove_quotes:
                    arg = remove_quotes.group(1)
                groups.append(arg)
                groups_dict["arg"] = arg

            groups_dict["kwargs"] = []
            arg_match = re.findall(r"^/%s\s[\'\"]?%s[\'\"]?\s(--\w+\s(?:\"(?:\w+\s)+\"|\w+))" % (groups_dict["command"], groups_dict["arg"]), message)
            if arg_match:
                for group in arg_match:
                    breakout = re.match(r"--(?P<kwarg_name>\w+)\s(?P<kwarg_value>(?:\"(?:\w+\s)+\")|\w+)", group)
                    groups.append(breakout.group("kwarg_name"))
                    groups.append(breakout.group("kwarg_value"))

                    groups_dict["kwargs"].append((breakout.group("kwarg_name"), breakout.group("kwarg_value")))

        else:
            # Not a command message
            groups_dict["type"] = "message"
            groups_dict["message"] = message

        return groups_dict


class Worker(threading.Thread):
    TORRENT = {
        "category": {
            "movies": CATEGORY.MOVIES,
            "tv": CATEGORY.TV,
            "music": CATEGORY.MUSIC,
            "books": CATEGORY.BOOKS,
            "games": CATEGORY.GAMES,
            "applications": CATEGORY.APPLICATIONS,
            "xxx": CATEGORY.XXX,
        },
        "order": {
            "size": ORDER.SIZE,
            "files_count": ORDER.FILES_COUNT,
            "time_add": ORDER.AGE,
            "seeders": ORDER.SEED,
            "leechers": ORDER.LEECH,
            "asc": ORDER.ASC,
            "desc": ORDER.DESC,
        }
    }

    def __init__(self, user,  *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        if "timeout" in kwargs:
            self.max_timeout = kwargs["timeout"]
        else:
            self.max_timeout = 600  # 10 minute timeout by default.
        self._queue = Queue()
        self.awaiting_command = True
        self.user = user
        self.bot = TelegramBot(API_TOKEN)

        self.affirmative = ["yes", "yup", "yeah", "yea"]
        self.negative = ["no", "nope", "none", "negative"]

        self.finished_event = threading.Event()
        self.last_message_time = datetime.now()

    def _post_message(self, message, *args, **kwargs):
        # Figure out how to post a basic message
        self.bot.send_message(self.user, message).wait()
        pass

    def _add_to_queue(self, text):
        token_dict = Parser.tokenize(text)
        if token_dict["type"] == "command":
            func_str = token_dict["command"]
            try:
                function = getattr(self, func_str)
                arg = token_dict["arg"]
                kwargs = token_dict["kwargs"]
            except AttributeError:
                function = self._post_message
                arg = "Command not found! Please try another."
                kwargs = []

        elif token_dict["type"] == "message":
            arg = token_dict['message']
            function = None
            kwargs = []

        else:
            function = self._post_message
            arg = "Message not supported! Please try another."
            kwargs = []

        self._queue.put((function, arg, kwargs))
        if not self.finished_event.isSet():
            self.start()

    def run(self):
        while not self.finished_event.isSet() or self.time_since_last_message > self.max_timeout:
            function, arg, kwargs = self._queue.get()
            if self.awaiting_command and function is not None:
                function(arg, kwargs)
            elif self.awaiting_command and function is None:
                self._post_message("Server was expecting a command but it received a message instead.")
            elif self.awaiting_command is False and function is not None:
                self._post_message("Server was expecting a message but it received a command instead. Would you like "
                                   "to stop the previous command and run this one instead?",
                                   options=[self.affirmative, self.negative])
            elif self.awaiting_command is False and function is None:
                self.generic_response(arg, **kwargs)
            else:
                raise Exception("Beep")

    def generic_response(self, message, **kwargs):
        pass

    def torrent(self, search_term, options):
        page = 1
        category = None
        order = None
        for option, value in options:
            if option.split("-")[0] == "page":
                page = value
            elif option.split("-")[0] == "category":
                category = self.TORRENT["category"][value]
            elif option.split("-")[0] == "order":
                order = self.TORRENT["order"][value]
        torrents = Search(search_term, page=page, category=category, order=order)
        message = "We have found several torents for you.\nThey are:\n%s" % "\n".join(
            [str(i+1) + ".  %s" % x.name for i, x in enumerate(torrents)])
        self._post_message(message)
        self.finished_event.set()

    @property
    def time_since_last_message(self):
        delta = datetime.now() - self.last_message_time
        return delta.total_seconds()

    @time_since_last_message.setter
    def time_since_last_message(self, value):
        logger.debug("Cant set this generated value!")

if __name__ == "__main__":
    MessageServer().poll()
