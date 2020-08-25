from datetime import tzinfo, timezone
from threading import Lock

from kickbase_api.models.chat_item import ChatItem
from kickbase_api.models.feed_item import FeedItem, FeedType
from kickbase_api.models.feed_meta import FeedMeta
from kickbase_api.models.league_data import LeagueData
from kickbase_api.models.market import Market
from kickbase_api.models.market_player import MarketPlayer
from kickbase_api.models.market_player_offer import MarketPlayerOffer
from kickbase_api.models.player import PlayerPosition, PlayerStatus
from pymongo import MongoClient

from kickbase_bot import logger
from kickbase_bot.serialization import _serialize


class _Persistence:

    def __init__(self, mongo_host: str = "localhost", mongo_user: str = "", mongo_pwd: str = "",
                 mongo_db: str = "kkbs_bot", auth_mechanism="SCRAM-SHA-256"):
        logger.debug("Connecting to mongodb")
        self.mongo_client = MongoClient(mongo_host, username=mongo_user, password=mongo_pwd, authSource=mongo_db,
                                        authMechanism=auth_mechanism, connect=True)
        self.mongo_db = self.mongo_client[mongo_db]
        logger.debug("Connection succeeded")

        self.key_value_collection = self.mongo_db["key_value"]
        self.league_data_collection = self.mongo_db["league_data"]
        self.feed_item_collection = self.mongo_db["feed_item"]
        self.chat_item_collection = self.mongo_db["chat_item"]
        self.market_collection = self.mongo_db["market"]
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
            res = list(self.league_data_collection.find())
        league_data = []
        for r in res:
            ld = LeagueData()
            ld.__dict__ = r
            ld.creation_date = ld.creation_date.replace(tzinfo=timezone.utc)
            league_data.append(ld)
        return league_data
        
    def does_feed_item_exist(self, feed_item: FeedItem) -> bool:
        with self.db_mutex:
            return self.feed_item_collection.count_documents({'id': feed_item.id}) > 0

    def save_feed_item(self, feed_item: FeedItem):
        with self.db_mutex:
            self.feed_item_collection.replace_one({'id': feed_item.id}, _serialize(feed_item), True)

    def get_feed_items(self) -> [FeedItem]:
        with self.db_mutex:
            res = list(self.feed_item_collection.find())
        feed_items = []
        for r in res:
            fi = FeedItem()
            fi.__dict__ = r
            fi.date = fi.date.replace(tzinfo=timezone.utc)
            
            fm = FeedMeta()
            fm.__dict__ = r["meta"]
            fi.meta = fm
            fi.type = FeedType(fi.type)
            
            feed_items.append(fi)
        del res
        return feed_items

    def does_chat_item_exist(self, chat_item: ChatItem) -> bool:
        with self.db_mutex:
            return self.chat_item_collection.count_documents({'id': chat_item.id}) > 0

    def save_chat_item(self, chat_item: ChatItem):
        with self.db_mutex:
            self.chat_item_collection.replace_one({'id': chat_item.id}, _serialize(chat_item), True)

    def get_chat_items(self) -> [ChatItem]:
        with self.db_mutex:
            res = list(self.chat_item_collection.find())
        chat_items = []
        for r in res:
            ci = ChatItem()
            ci.__dict__ = r
            ci.date = ci.date.replace(tzinfo=timezone.utc)

            chat_items.append(ci)
        del res
        return chat_items
    
    def save_market(self, market: Market):
        if "date" not in market.__dict__:
            raise Exception("date property is required on Market item")
        with self.db_mutex:
            self.market_collection.replace_one({'date': market.date}, _serialize(market), True)
    
    def get_markets(self, contain_player_id: str = None, limit: int = None) -> [Market]:
        cond = {}
        if contain_player_id is not None:
            cond["players"] = { "$elemMatch": { "id": contain_player_id }}
        with self.db_mutex:
            if limit is not None:
                res = list(self.market_collection.find(cond).sort({"date": -1}).limit(limit))
            else:
                res = list(self.market_collection.find(cond).sort({"date": -1}))
        markets = []
        for r in res:
            market = Market()
            market.__dict__ = r
            market.date = r['date'].replace(tzinfo=timezone.utc)
            
            players = []
            for p in market.players:
                player = MarketPlayer()
                player.__dict__ = p
                player.position = PlayerPosition(player.position)
                player.status = PlayerStatus(player.status)
                players.append(player)
                
                offers = []
                if hasattr(player, "offers") and player.offers is not None:
                    for o in player.offers:
                        offer = MarketPlayerOffer()
                        offer.__dict__ = o
                        offer.date = o['date'].replace(tzinfo=timezone.utc)
                        if "valid_until_date" in o:
                            offer.valid_until_date = o['valid_until_date'].replace(tzinfo=timezone.utc)
                        offers.append(offer)
                player.offers = offers
                
            market.players = players
            
            markets.append(market)
        del res
        return markets
