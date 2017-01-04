#!/usr/bin/python
import subprocess
import shlex
import yaml
import time
from time import sleep
from threading import Thread
from ISStreamer.Streamer import Streamer
import sys
import re
from logging import debug,info
import logging
import telegrambot

# Config files
hosts_file  = 'known_hosts.yml'
config_file = 'config.yml'
log_level = logging.INFO

logging.basicConfig(stream=sys.stderr, level=log_level)

# Get access_key, bucket_key, bucket_name from config
with open(config_file, 'r') as readfile:
    cfg = yaml.load(readfile)

# Error check config
# TODO: scan_frequency must be present and integer

def read_hosts_file(hosts_file):

    # Get list of known/seen MAC addresses
    with open(hosts_file, 'r') as readfile:
        hosts = yaml.safe_load(readfile)

    debug("Known MAC - Hosts:")
    for mac in hosts['known']:
        debug("\t%s %s" % (mac, hosts['known'][mac]))

    return hosts


# Initialize the Initial State streamer
# Be sure to add your unique access key to config
streamer = Streamer(bucket_name=cfg['bucket_name'], bucket_key=cfg['bucket_name'], access_key=cfg['access_key'])

# Function that checks for device presence
def whosHere(i):

    # 30 second pause to allow main thread to finish arp-scan and populate output
    sleep(30)

    # Loop through checking for devices and counting if they're not present
    while True:

        # Exits thread if Keyboard Interrupt occurs
        if stop == True:
            print "Exiting Thread"
            exit()
        else:
            pass

        # If a listed device address is present print and stream
        if address[i] in output:
            print(occupant[i] + "'s device is connected to your network")
            if presentSent[i] == 0:
                # Stream that device is present
                streamer.log(occupant[i],":office:")
                streamer.flush()
                print(occupant[i] + " present streamed")
                # Reset counters so another stream isn't sent if the device
                # is still present
                firstRun[i] = 0
                presentSent[i] = 1
                notPresentSent[i] = 0
                counter[i] = 0
                sleep(900)
            else:
                # If a stream's already been sent, just wait for 15 minutes
                counter[i] = 0
                sleep(900)
        # If a listed device address is not present, print and stream
        else:
            print(occupant[i] + "'s device is not present")
            # Only consider a device offline if it's counter has reached 30
            # This is the same as 15 minutes passing
            if counter[i] == 30 or firstRun[i] == 1:
                firstRun[i] = 0
                if notPresentSent[i] == 0:
                    # Stream that device is not present
                    streamer.log(occupant[i],":no_entry_sign::office:")
                    streamer.flush()
                    print(occupant[i] + " not present streamed")
                    # Reset counters so another stream isn't sent if the device
                    # is still present
                    notPresentSent[i] = 1
                    presentSent[i] = 0
                    counter[i] = 0
                else:
                    # If a stream's already been sent, wait 30 seconds
                    counter[i] = 0
                    sleep(30)
            # Count how many 30 second intervals have happened since the device
            # disappeared from the network
            else:
                counter[i] = counter[i] + 1
                print(occupant[i] + "'s counter at " + str(counter[i]))
                sleep(30)

def find_active_macs(ip_range):
        macs_found = {}

        nmap = "nmap -sP  %s" % ip_range
        args = shlex.split(nmap)
        debug("Running: %s" % args)
        nmap_output = subprocess.check_output(args, shell=True)
        debug(nmap_output)

        split_text = nmap_output.split('Nmap scan report for ')[1:]

        for line in split_text:
            # Nmap scan report for 192.168.1.13\n Host is up (0.034s latency).\n MAC Address: 60:38:E0:62:40:95 (Unknown)
            match = re.match(r"^([\d.]+).*MAC Address: ([\dA-Fa-f:]+) \((.*)\)", line, re.DOTALL)
            # Match group:  1-IP  2-MAC  3-MAC Vendor
            if match:
                debug( match.group(2), match.group(1), match.group(3))
                macs_found[match.group(2)] =  match.group(1) +' | ' + match.group(3) + ' | ' + time.strftime("%c")
        return macs_found

def write_yaml_hosts(hosts, hosts_file):
    with open(hosts_file, 'w') as outfile:
        yaml.dump(hosts, outfile, default_flow_style=False)

# Main thread

if __name__ == '__main__':

    try:
        while True:
            # Perform NMAP ping sweep to find active hosts/macs
            macs_found = find_active_macs(cfg['ip_range'])

            # Read in known/seen MACs from file
            hosts = read_hosts_file(hosts_file)

            print "Found %d MACs" % len(macs_found)

            for mac in macs_found:
                if mac in hosts['known']:
                    debug("Known : "+ mac)
                else:
                    # MAC is not listed in known_hosts.yml under "known"

                    if 'seen' not in  hosts or not hosts['seen']: # initialize if not present (ugly!)
                        hosts['seen'] = {}

                    if mac in hosts['seen']:
                        # MAC is unknown (unlabled in known_hosts.yml) but has been seen before
                        print "Seen :    ", mac
                    else:
                        desc = mac + ' | ' + macs_found[mac]
                        print "Unknown : %s" % (desc)
                        telegrambot.send_to_telegram(desc, cfg['telegram_token'], cfg['telegram_chat_id'])
                        hosts['seen'][mac] = macs_found[mac]

                    write_yaml_hosts(hosts, hosts_file)

            # Wait 30 seconds between scans
            sleep(cfg['scan_frequency'])

    except KeyboardInterrupt:
        # On a keyboard interrupt signal threads to exit
        write_yaml_hosts(hosts, hosts_file)
