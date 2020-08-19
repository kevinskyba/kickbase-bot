import copy
from threading import Thread
from typing import Callable

from kickbase_api.kickbase import Kickbase
from kickbase_api.models.chat_item import ChatItem
from kickbase_api.models.feed_item import FeedItem
from kickbase_api.models.league_data import LeagueData

from kickbase_bot import logger
from kickbase_bot.persistence import _Persistence
from kickbase_bot.threading import _start_thread_periodically


class KickbaseBot:
    
    _periodic_feed_thread: Thread
    _periodic_chat_thread: Thread
    
    _leagues: [LeagueData] = []
    selected_league: LeagueData = None
    
    _feed_item_callback: [Callable[[FeedItem, 'KickbaseBot'], None]] = []
    _chat_item_callback: [Callable[[ChatItem, 'KickbaseBot'], None]] = []

    def __init__(self, **kwargs):
        self.kickbase_api = Kickbase(
            google_identity_toolkit_api_key=kwargs.get('google_identity_toolkit_api_key', None))
        self._persistence = _Persistence(
            mongo_host=kwargs.get('mongodb_host', 'localhost'),
            mongo_user=kwargs.get('mongodb_user', ''),
            mongo_pwd=kwargs.get('mongodb_password', ''),
            mongo_db=kwargs.get('mongodb_db', 'kkbs_bot')
        )
        
        self._periodic_feed_interval = kwargs.get("periodic_feed_interval", 15)
        self._periodic_chat_interval = kwargs.get("periodic_chat_interval", 5)
    
    def connect(self, username, password):
        logger.debug("Login using username %s", username)
        me, self._leagues = self.kickbase_api.login(username, password)
        logger.debug("Login succeeded")
        
    def add_feed_item_callback(self, func: Callable[[FeedItem, 'KickbaseBot'], None]):
        self._feed_item_callback.append(func)

    def add_chat_item_callback(self, func: Callable[[ChatItem, 'KickbaseBot'], None]):
        self._chat_item_callback.append(func)
        
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
                        if not self._persistence.does_feed_item_exist(feed_item):
                            logger.debug("New feed item: %s", feed_item.id)
                            new_feed_item = True
                            for cb in self._feed_item_callback:
                                if not silent:
                                    cb(copy.deepcopy(feed_item), self)
                        self._persistence.save_feed_item(feed_item)
                    
                    if not new_feed_item:
                        break
                            
                    count = count + len(feed_items)
    
            logger.debug("Fetched %s feed items", len(feed_items))
        except Exception as ex:
            logger.error("Something went wrong fetching feed items: %s", ex)

    def _periodic_chat(self, silent=False):
        try:
            # Fetch chat items
            logger.debug("Fetching chat items")
            chat_items = self.kickbase_api.chat_messages(self.selected_league)
            for chat_item in chat_items:
                if not self._persistence.does_chat_item_exist(chat_item):
                    logger.debug("New chat item: %s (%s)", chat_item.id, chat_item.message)
                    for cb in self._chat_item_callback:
                        if not silent:
                            cb(copy.deepcopy(chat_item), self)
                self._persistence.save_chat_item(chat_item)

            logger.debug("Fetched %s chat items", len(chat_items))
        except Exception as ex:
            logger.error("Something went wrong fetching chat items: %s", ex)
            
    def run(self, league_id):
        saved_league_id = self._persistence.get_value("league_id")
        if saved_league_id is not None and saved_league_id != league_id:
            raise Exception("The database is based on a different league_id. Please specify a different database.")
        self._persistence.save_value("league_id", league_id)
        
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
        
        logger.debug("Starting threads...")
        threads = []
        
        logger.debug("Feed update interval was set to %s seconds", self._periodic_feed_interval)
        self._periodic_feed_thread = _start_thread_periodically(self._periodic_feed_interval, self._periodic_feed)
        threads.append(self._periodic_feed_thread)
        
        logger.debug("Chat update interval was set to %s seconds", self._periodic_chat_interval)
        self._periodic_chat_thread = _start_thread_periodically(self._periodic_chat_interval, self._periodic_chat)
        threads.append(self._periodic_chat_thread)
        
        logger.debug("All threads started")
        for thread in threads:
            thread.join()
