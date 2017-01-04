#!/usr/bin/python

import telegram
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
import logging
import yaml


# http://telegram.me/homepresencebot

def send_to_telegram(txt, telegram_token, chat_id):
    bot = telegram.Bot(token=telegram_token)
    bot.sendMessage(chat_id=chat_id, text=txt)

# Sets an "accept" "block" keyboard for this chat
def set_custom_keyboard(telegram_token, chat_id ):
    # custom_keyboard = [['top-left', 'top-right'],
    #                     ['bottom-left', 'bottom-right']]
    bot = telegram.Bot(token=telegram_token)

    custom_keyboard = [["Accept", "Block"]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)

    bot.sendMessage(chat_id=chat_id,
                      text="Custom Keyboard Test",
                      reply_markup=reply_markup)

def junk():
    #print "Logged into: ", bot.getMe()['first_name']

    for msg in bot.getUpdates():
        print msg.message.chat_id
        #print yaml.dump(msg.message, default_flow_style=False, default_style='')
        print


    chat_id = bot.getUpdates()[-1].message.chat_id
    chat_id = 325815706

    bot.sendMessage(chat_id=chat_id, text="Received")

def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="I'm a Bot, please chat with me")

def echo(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text=update.message.text)

def caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    bot.sendMessage(chat_id=update.message.chat_id, text=text_caps)

def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")

def listen(telegram_token):
    updater = Updater(token=telegram_token)
    dispatcher = updater.dispatcher
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(Filters.text, echo)
    caps_handler = CommandHandler('caps', caps, pass_args=True)
    unknown_handler = MessageHandler(Filters.command, unknown)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(caps_handler)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':

    with open(config_file, 'r') as readfile:
        cfg = yaml.load(readfile)

    listen(cfg['telegram_token'])

    #send_to_telegram('test', cfg['telegram_token'], cfg['telegram_chat_id'])
