# Kickbase_Bot
[Kickbase](https://www.kickbase.com/) bot framework for Python 3.  This work is unofficial and not related to kickbase in any way. All of this was done for scientific reasons only and you should not use it for anything else but for your personal learning!

## Installation
- From pypi:
`pip3 install kickbase_bot`

## Requirements
- [kickbase_api](https://github.com/kevinskyba/kickbase-api-python/)
- [pymongo](https://github.com/mongodb/mongo-python-driver)

## Usage
```python
# Press the green button in the gutter to run the script.
import logging

from kickbase_api.models.chat_item import ChatItem
from kickbase_api.models.feed_item import FeedItem, FeedType

from kickbase_bot import logger as kickbase_logger
from kickbase_bot.kickbase_bot import KickbaseBot

sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
kickbase_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
sh.setFormatter(formatter)
kickbase_logger.addHandler(sh)


def on_feed_item(feed_item: FeedItem, bot: KickbaseBot):
    pass


def on_chat_item(chat_item: ChatItem, bot: KickbaseBot):
    if chat_item.user_id != bot.kickbase_api.user.id:
        print("Got chat: " + chat_item.message + " from: " + chat_item.username)
        bot.kickbase_api.post_chat_message("Hey {}".format(chat_item.username), bot.selected_league)


if __name__ == '__main__':
    kkbs_bot = KickbaseBot(periodic_feed_interval=5,
                           google_identity_toolkit_api_key="example",
                           mongodb_host="localhost",
                           mongodb_user="kkbs_bot", mongodb_password="kkbs_bot")
    kkbs_bot.connect("example", "example_password")

    kkbs_bot.add_feed_item_callback(on_feed_item)
    kkbs_bot.add_chat_item_callback(on_chat_item)

    kkbs_bot.run("example_league_id")
```

## Docs


## API


## License

[MIT License](LICENSE.md)