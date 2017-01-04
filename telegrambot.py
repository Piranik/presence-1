#!/usr/bin/python

import telegram
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
import logging
import yaml
import re

# http://telegram.me/homepresencebot

def send_to_telegram(txt, telegram_token, chat_id):
    bot = telegram.Bot(token=telegram_token)
    bot.sendMessage(chat_id=chat_id, text=txt)

# not used
# Sets an "accept" "block" custom keyboard for this chat
def set_custom_keyboard(telegram_token, chat_id ):
    # custom_keyboard = [['top-left', 'top-right'],
    #                     ['bottom-left', 'bottom-right']]
    bot = telegram.Bot(token=telegram_token)

    custom_keyboard = [["Accept", "Block"]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)

    bot.sendMessage(chat_id=chat_id,
                      text="Custom Keyboard Test",
                      reply_markup=reply_markup)


def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="I'm a Bot, please chat with me")

def echo(bot, update):
    mac = new_description = None

    # To modify database/yaml either accept:
    #  1) a reply to a Bot post saying new MAC Found
    #  2) message formatted: MAC New_Description

    # Checking Case 2
    match = re.match(r"(^\s*[\dA-Fa-f:]{17})\s*(.*)", update.message.text)  # Match mac addr ex: 58:55:ca:0d:28:XX New description
    if match and len(match.groups()) == 2:
        mac = match.group(1).upper()
        new_description = match.group(2)

    # Checking Case 1
    try:
        reply_original = update.message['reply_to_message']['text']
        #print "**REPLY:", reply_original
        # match = re.match(r"^\s([\dA-Fa-f:]{17})")  # Match mac addr ex: 58:55:ca:0d:28:XX
        match = re.match(r"(^\s*[\dA-Fa-f:]{17})", reply_original)  # Match mac addr ex: 58:55:ca:0d:28:XX
        if match:
            mac = match.group(1).upper()
            new_description = update.message.text
    except:
        pass

    if mac and new_description:
        update_yaml(mac, new_description)
        bot.sendMessage(chat_id=update.message.chat_id, text="Updating %s with description: %s" % (mac, new_description))
    else:
        bot.sendMessage(chat_id=update.message.chat_id, text="Can't hear ya")

def update_yaml(mac, new_description):
    # Convert to ASCII since telegram uses unicode
    mac = mac.encode('ascii','ignore')
    new_description = new_description.encode('ascii','ignore')

    print "Updating %s with description: %s" % (mac, new_description)

    hosts = load_known_hosts('known_hosts.yml')

    # Remove mac from "seen" if existings
    if mac in hosts['seen']:
        del hosts['seen'][mac]

    # Remove mac from "known" if existings
    if mac in hosts['known']:
        del hosts['known'][mac]

    # Add or overwrite mac in 'known' section
    hosts['known'][mac] = new_description

    # Write out the file to save it
    write_yaml_hosts(hosts, hosts_file)

def list_hosts(bot, update):
    hosts = load_known_hosts(hosts_file)
    hosts_pretty = yaml.dump(hosts, default_flow_style=False)
    print hosts_pretty

    bot.sendMessage(chat_id=update.message.chat_id, text=hosts_pretty)

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

    # TODO add security handler to drop unauthorized users

    start_handler = CommandHandler('start', start)
    list_handler = CommandHandler('list', list_hosts)
    echo_handler = MessageHandler(Filters.text, echo)
    caps_handler = CommandHandler('caps', caps, pass_args=True)
    unknown_handler = MessageHandler(Filters.command, unknown)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(list_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(caps_handler)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()
    updater.idle()

def write_yaml_hosts(hosts, hosts_file):
    with open(hosts_file, 'w') as outfile:
        yaml.dump(hosts, outfile, default_flow_style=False)

def load_known_hosts(yamlfile):
    with open(yamlfile, 'r') as readfile:
        cfg = yaml.load(readfile)
    return cfg

if __name__ == '__main__':

    hosts_file  = 'known_hosts.yml'
    config_file = 'config.yml'

    cfg   = load_known_hosts(config_file)
    hosts = load_known_hosts(hosts_file)

    listen(cfg['telegram_token'])

    #send_to_telegram('test', cfg['telegram_token'], cfg['telegram_chat_id'])
