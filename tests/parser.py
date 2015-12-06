__author__ = 'Alex'
from v2 import Parser
import unittest


class Parser_Tester(unittest.TestCase):
    def setUp(self):
        self.str_1 = "/torrent Superman --created_by Alex"
        self.str_2 = '/torrent "Superman and the mighty grail" --created_by Alex'
        self.str_3 = '/torrent "Superman --created_by Alex"'
        self.str_4 = "Wow that's a super cool message you sent me, thanks!"
        self.str_5 = "/torrent  Crazy"

        self.result1 = {'command': 'torrent',
                        'arg': 'Superman',
                        "type": "command",
                        'kwargs': [
                            ('created_by', 'Alex')
                        ]}
        self.result2 = {'command': 'torrent',
                        'arg': 'Superman and the mighty grail',
                        "type": "command",
                        'kwargs': [
                            ('created_by', 'Alex')
                        ]}
        self.result3 = {'command': 'torrent',
                        'arg': 'Superman --created_by Alex',
                        "type": "command",
                        'kwargs': []}
        self.result4 = {"type": "message",
                        "message": "Wow that's a super cool message you sent me, thanks!"}
        self.result5 = {"command": "torrent",
                        "arg": "Crazy",
                        "type": "command",
                        "kwargs": []}

    def test_parsing_torrent(self):
        result1 = Parser.tokenize(self.str_1)
        result2 = Parser.tokenize(self.str_2)
        result3 = Parser.tokenize(self.str_3)
        result4 = Parser.tokenize(self.str_4)
        result5 = Parser.tokenize(self.str_5)

        self.assertEqual(result1, self.result1)
        self.assertEqual(result2, self.result2)
        self.assertEqual(result3, self.result3)
        self.assertEqual(result4, self.result4)
        self.assertEqual(result5, self.result5)


if __name__ == "__main__":
    unittest.main()
