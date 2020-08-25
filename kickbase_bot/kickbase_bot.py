import copy
from datetime import datetime
from threading import Thread
from typing import Callable

from kickbase_api.kickbase import Kickbase
from kickbase_api.models.chat_item import ChatItem
from kickbase_api.models.feed_item import FeedItem
from kickbase_api.models.league_data import LeagueData
from kickbase_api.models.market import Market

from kickbase_bot import logger
from kickbase_bot.persistence import _Persistence
from kickbase_bot.threading import _start_thread_periodically


class KickbaseBot:
    
    _periodic_feed_thread: Thread
    _periodic_chat_thread: Thread
    _periodic_market_thread: Thread

    _leagues: [LeagueData] = []
    selected_league: LeagueData = None
    
    _feed_item_callback: [Callable[[FeedItem, 'KickbaseBot'], None]] = []
    _chat_item_callback: [Callable[[ChatItem, 'KickbaseBot'], None]] = []
    _market_callback: [Callable[[Market, 'KickbaseBot'], None]] = []

    def __init__(self, **kwargs):
        self.kickbase_api = Kickbase(
            google_identity_toolkit_api_key=kwargs.get('google_identity_toolkit_api_key', None))
        self.persistence = _Persistence(
            mongo_host=kwargs.get('mongodb_host', 'localhost'),
            mongo_user=kwargs.get('mongodb_user', ''),
            mongo_pwd=kwargs.get('mongodb_password', ''),
            mongo_db=kwargs.get('mongodb_db', 'kkbs_bot'),
            auth_mechanism=kwargs.get('mongodb_auth_mechanism', 'SCRAM-SHA-256')
        )
        
        self._periodic_feed_interval = kwargs.get("periodic_feed_interval", 15)
        self._periodic_chat_interval = kwargs.get("periodic_chat_interval", 5)
        self._periodic_market_interval = kwargs.get("periodic_market_interval", 60)

    def connect(self, username, password):
        logger.debug("Login using username %s", username)
        me, self._leagues = self.kickbase_api.login(username, password)
        logger.debug("Login succeeded")
        
    def add_feed_item_callback(self, func: Callable[[FeedItem, 'KickbaseBot'], None]):
        self._feed_item_callback.append(func)

    def add_chat_item_callback(self, func: Callable[[ChatItem, 'KickbaseBot'], None]):
        self._chat_item_callback.append(func)

    def add_market_item_callback(self, func: Callable[[Market, 'KickbaseBot'], None]):
        self._market_callback.append(func)
        
    def _periodic_feed(self, silent=False):
        try:
            # Fetch all feed items
            count = 0
            while True:
                logger.debug("Fetching feed items, start: %s", count)
                feed_items = self.kickbase_api.league_feed(count, self.selected_league)
                if len(feed_items) == 0:
                    break
                else:
                    new_feed_item = False
                    for feed_item in feed_items:
                        exists = self.persistence.does_feed_item_exist(feed_item)
                        self.persistence.save_feed_item(feed_item)
                        if not exists:
                            logger.debug("New feed item: %s", feed_item.id)
                            new_feed_item = True
                            for cb in self._feed_item_callback:
                                if not silent:
                                    try:
                                        cp = copy.deepcopy(feed_item)
                                        cb(cp, self)
                                        del cp
                                    except Exception as ex:
                                        logger.error("[{}] Error in feed callback: ".format(feed_item.id) + str(ex))
                                        
                    if not new_feed_item:
                        break
                            
                    count = count + len(feed_items)
                del feed_items
    
            logger.debug("Fetched %s feed items", count)
        except Exception as ex:
            logger.error("Something went wrong fetching feed items: %s", ex)

    def _periodic_chat(self, silent=False):
        try:
            # Fetch chat items
            logger.debug("Fetching chat items")
            count = 0
            next_page_token = None
            while True:
                chat_items, next_page_token = self.kickbase_api.chat_messages(self.selected_league,
                                                                              page_size=100,
                                                                              next_page_token=next_page_token)
                count = count + len(chat_items)
                for chat_item in chat_items:
                    exists = self.persistence.does_chat_item_exist(chat_item)
                    self.persistence.save_chat_item(chat_item)
                    if not exists:
                        logger.debug("New chat item: %s (%s)", chat_item.id, chat_item.message)
                        for cb in self._chat_item_callback:
                            if not silent:
                                try:
                                    cp = copy.deepcopy(chat_item)
                                    cb(cp, self)
                                    del cp
                                except Exception as ex:
                                    logger.error("[{}] Error in chat callback: ".format(chat_item.id) + str(ex))
                                    
                del chat_items
                if next_page_token is None:
                    break

            logger.debug("Fetched %s chat items", count)
        except Exception as ex:
            logger.error("Something went wrong fetching chat items: %s", ex)
            
    def _periodic_market(self, silent=False):
        try:
            logger.debug("Fetching market")
            market = self.kickbase_api.market(self.selected_league)
            market.date = datetime.utcnow()
            self.persistence.save_market(market)
            for cb in self._market_callback:
                if not silent:
                    try:
                        cp = copy.deepcopy(market)
                        cb(cp, self)
                        del cp
                    except Exception as ex:
                        logger.error("Error in market callback: " + str(ex))
            del market
            logger.debug("Fetched market")
        except Exception as ex:
            logger.error("Something went wrong fetching market: %s", ex)
            
    def initialize(self, league_id):
        saved_league_id = self.persistence.get_value("league_id")
        if saved_league_id is not None and saved_league_id != league_id:
            raise Exception("The database is based on a different league_id. Please specify a different database.")
        self.persistence.save_value("league_id", league_id)

        for league in self._leagues:
            if league.id == league_id:
                self.selected_league = league
                logger.debug("Selected league: %s", self.selected_league.name)

        if self.selected_league is None:
            logger.error("League with id %s could not be found", league_id)
            logger.error("Available leagues are:")
            for league in self._leagues:
                logger.error("%s [%s]", league.name, league.id)
            raise Exception("League not found".format(league_id))
        
    def run(self):
        logger.debug("Starting threads...")
        threads = []
        
        logger.debug("Feed update interval was set to %s seconds", self._periodic_feed_interval)
        self._periodic_feed_thread = _start_thread_periodically(self._periodic_feed_interval, self._periodic_feed)
        threads.append(self._periodic_feed_thread)
        
        logger.debug("Chat update interval was set to %s seconds", self._periodic_chat_interval)
        self._periodic_chat_thread = _start_thread_periodically(self._periodic_chat_interval, self._periodic_chat)
        threads.append(self._periodic_chat_thread)
        
        logger.debug("Market update interval was set to %s seconds", self._periodic_market_interval)
        self._periodic_market_thread = _start_thread_periodically(self._periodic_market_interval, self._periodic_market)
        threads.append(self._periodic_market_thread)
        
        logger.debug("All threads started")
        for thread in threads:
            thread.join()
