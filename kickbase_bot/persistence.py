from threading import Lock

from kickbase_api.models.chat_item import ChatItem
from kickbase_api.models.feed_item import FeedItem
from kickbase_api.models.league_data import LeagueData
from pymongo import MongoClient

from kickbase_bot import logger
from kickbase_bot.serialization import _serialize


class _Persistence:

    def __init__(self, mongo_host: str = "localhost", mongo_user: str = "", mongo_pwd: str = "",
                 mongo_db: str = "kkbs_bot"):
        logger.debug("Connecting to mongodb")
        self.mongo_client = MongoClient(mongo_host, username=mongo_user, password=mongo_pwd, authSource=mongo_db,
                                        authMechanism="SCRAM-SHA-256")
        self.mongo_client.admin.command("ismaster")  # Check connection
        self.mongo_db = self.mongo_client[mongo_db]
        logger.debug("Connection succeeded")

        self.key_value_collection = self.mongo_db["key_value"]
        self.league_data_collection = self.mongo_db["league_data"]
        self.feed_item_collection = self.mongo_db["feed_item"]
        self.chat_item_collection = self.mongo_db["chat_item"]
        self.db_mutex = Lock()

    def save_value(self, key: str, value: any):
        with self.db_mutex:
            self.key_value_collection.replace_one({'key': key}, {
                "key": key,
                "value": value
            }, True)

    def get_value(self, key: str) -> any:
        with self.db_mutex:
            res = self.key_value_collection.find_one({'key': key})
            if res is not None:
                return res["value"]
            else:
                return None

    def does_league_data_exist(self, league_data: LeagueData) -> bool:
        with self.db_mutex:
            return self.league_data_collection.count_documents({'id': league_data.id}) > 0

    def save_league_data(self, league_data: LeagueData):
        with self.db_mutex:
            self.league_data_collection.replace_one({'id': league_data.id}, _serialize(league_data), True)

    def get_league_data(self) -> [LeagueData]:
        with self.db_mutex:
            return self.league_data_collection.find()

    def does_feed_item_exist(self, feed_item: FeedItem) -> bool:
        with self.db_mutex:
            return self.feed_item_collection.count_documents({'id': feed_item.id}) > 0

    def save_feed_item(self, feed_item: FeedItem):
        with self.db_mutex:
            self.feed_item_collection.replace_one({'id': feed_item.id}, _serialize(feed_item), True)

    def get_feed_items(self) -> [FeedItem]:
        with self.db_mutex:
            return self.feed_item_collection.find()

    def does_chat_item_exist(self, chat_item: ChatItem) -> bool:
        with self.db_mutex:
            return self.chat_item_collection.count_documents({'id': chat_item.id}) > 0

    def save_chat_item(self, chat_item: ChatItem):
        with self.db_mutex:
            self.chat_item_collection.replace_one({'id': chat_item.id}, _serialize(chat_item), True)

    def get_chat_items(self) -> [ChatItem]:
        with self.db_mutex:
            return self.chat_item_collection.find()
