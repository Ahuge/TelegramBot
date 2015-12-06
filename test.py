from twx.botapi import TelegramBot, ReplyKeyboardMarkup
from KickassAPI import Search, Latest, User, CATEGORY, ORDER
import time
from pprint import pprint
import shlex
from threading import Thread
from api_token import API_TOKEN

__author__ = 'Alex'

bot = TelegramBot(API_TOKEN)
bot.update_bot_info().wait()
print(bot.username)
user_id = int(170007825)

# """
# Send a message to a user
# """
#
# result = bot.send_message(user_id, 'test message body').wait()
# print(result)
#
# """
# Get updates sent to the bot
# """
# updates = bot.get_updates().wait()
# for update in updates:
#     print(update)

"""
Use a custom keyboard
"""
# keyboard = [
#     ['Pirates of the carribean'],
#     ['4', '5', '6'],
#     ['1', '2', '3'],
#          ['0']
# ]
# reply_markup = ReplyKeyboardMarkup.create(keyboard, one_time_keyboard=True)

# bot.send_message(user_id, 'please enter a number', reply_markup=reply_markup).wait()


class BotWorker(Thread):
    COMMANDS = dict([("TORRENT", lambda: TorrentBot)])


    def __init__(self, update):
        super(BotWorker, self).__init__()
        self.message = update.message

    def run(self):
        raise NotImplementedError("Command not found!")

    @staticmethod
    def create_bot(message):
        bot = BotWorker.evaluate_message(message)
        return bot

    @classmethod
    def evaluate_message(cls, message):
        text = message.text
        if text.startswith("/"):
            # Look for command
            command, arg, optional = BotWorker.tokenize(text)
            if command[1:].upper() in cls.COMMANDS:
                # I understand this
                botcls = cls.COMMANDS[command[1:].upper()]()
                bot =  botcls(arg, optional)
                return bot

    @staticmethod
    def tokenize(text):
        tokens = shlex.split(text)
        optional = ()
        if len(tokens) > 2:
            # Has optional tokens
            command, arg = tokens[:2]
            optional = zip(tokens[2::2], tokens[3::2])
        else:
            command, arg = tokens

        return command, arg, optional


class TorrentBot(BotWorker):

    def __init__(self, arg, optional):
        self.arg = arg
        self.optional = optional

    def run(self):
        self.search()

    def search(self):
        for t in Search(self.arg):
            t.return_lookup()


class BotServer(object):
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

    MODES = ["torrent.search"]

    def __init__(self):
        self.bot = TelegramBot(API_TOKEN)
        self.updates = set(bot.get_updates().wait())
        self.users_mode = {}
        self.thread = Thread(target=self.call_factory)

    def call_factory(self):
        pass

    @staticmethod
    def isqrt(n):
        print(n)
        x = n
        y = (x + 1) // 2
        last_x = x
        while y < x:
            x = y
            y = (x + n // x) // 2
            last_x = x
        print(last_x + 1)
        return last_x + 1

    def search_torrent(self, search_term, options):
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
        return torrents

    def download_torrent(self, number, torrents):
        torrent = torrents[int(number)]
        print(torrent["magnet_link"])

    def build_keyboard(self, xy, iterable_obj):
        print("Building Base keyboard")
        keyboard = []

        count = 0
        r_count = 0
        len_itter = len(iterable_obj)
        print("Building Custom keyboard")
        for row in range(xy):
            c_count = 0
            print(keyboard)
            print(r_count)
            keyboard.append([])
            for col in range(xy):
                if count < len_itter:
                    keyboard[r_count].append(count)
                    # for i, x in enumerate(iterable_obj):
                    #     if i == count:
                    #         print("Modifying keyboard at %s, %s from value %s" % (r_count, c_count, x))
                    #         keyboard[r_count][c_count] = x['name']
                count += 1
                c_count += 1
            r_count += 1
        return keyboard

    def build_message(self, style, result, _id=None):
        if _id:
            if style == "torrent.search":
                print("Building Message")
                msg = "We have found several torents for you.\nThey are:\n%s\n\nPleas" % "\n".join([str(i) + ".  %s" % x.name for i, x in enumerate(result)])
                print("Building keyboard")
                keyboard = self.build_keyboard(self.isqrt(len(result)), result)
                print("Building Markup")
                pprint(keyboard)
                reply_markup = ReplyKeyboardMarkup.create(keyboard, one_time_keyboard=True)
                print("Sending Message")
                self.bot.send_message(_id, msg, reply_markup=reply_markup).wait()

    def start(self):
        COMMANDS = {
            "TORRENT": self.search_torrent
        }
        while True:
            print("Waiting....")
            updates = set(self.bot.get_updates().wait())
            new_updates = updates.difference(self.updates)
            for update in new_updates:
                text = update.message.text
                if str(update.message.sender.id) in self.users_mode:
                    command = self.users_mode[str(update.message.sender.id)]["command"]
                    torrents = self.users_mode[str(update.message.sender.id)]["data"]
                    command(update.message.text, torrents)

                if text.startswith("/"):
                    # Look for command
                    command, arg, optional = BotWorker.tokenize(text)
                    if command[1:].upper() in COMMANDS:
                        # I understand this
                        function = COMMANDS[command[1:].upper()]
                        result = function(arg, optional)
                        print("Got results")
                        if result:
                            self.users_mode[str(update.message.sender.id)] = {"command": self.download_torrent, "data": result}
                            print("Updating user status")
                            self.build_message("torrent.search", result, _id=update.message.sender.id)



b = BotServer()

b.start()


# cur_status = {
#     "updates": set([]),
#     "mode": None,
# }
# intt = 0
# while True:
#     updates = set(bot.get_updates().wait())
#     new_updates = updates.difference(cur_status['updates'])
#     cur_status['updates'] = updates
#     for update in new_updates:
#         print(update.message.text)
#
#     print("---------")
#     intt += 1
#     if intt > 60:
#         break
#     time.sleep(1)
import socket
socket.socket.recvfrom(8192)
