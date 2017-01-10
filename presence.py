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
import datetime

# Config files
hosts_file  = 'known_hosts.yml'
config_file = 'config.yml'
log_level = logging.INFO
deliminator = ' | '
#re_date = re.compile(r"")

logging.basicConfig(stream=sys.stderr, level=log_level)

# Get access_key, bucket_key, bucket_name from config
with open(config_file, 'r') as readfile:
    cfg = yaml.load(readfile)

# Error check config
# TODO: scan_frequency must be present and integer


# Initialize the Initial State streamer
# Be sure to add your unique access key to config
#streamer = Streamer(bucket_name=cfg['bucket_name'], bucket_key=cfg['bucket_name'], access_key=cfg['access_key'])


def write_yaml_hosts(hosts, hosts_file):
    with open(hosts_file, 'w') as outfile:
        yaml.dump(hosts, outfile, width=1000, default_flow_style=False)

# Main thread
class Device():
    description = ''
    hostname = ''
    mac = ''
    mac_vendor = ''
    ip = ''
    first_date = ''
    last_date = ''


    def __init__(self):
        pass

    def __init__(self, mac, device_string):
        #print "Creating new Device: ", mac, device_string

        self.mac = mac
        temp = map(str.strip, device_string.split(deliminator)) # Remove trailing spaces
        temp = map(str.lstrip, temp)    # Remove leading spaces
        (self.hostname, self.mac_vendor, self.ip, self.first_date, self.last_date) = temp

    def __str__(self):
        arr = [self.hostname, self.mac_vendor, self.ip, str(self.first_date), str(self.last_date)]
        return self.mac + ': ' + deliminator.join(arr)

    def data(self):
        arr = [self.hostname, self.mac_vendor, self.ip, str(self.first_date), str(self.last_date)]
        return  deliminator.join(arr)

    def print_verbose(self):
        print "\t'"   + self.mac + "'"
        print "\t\t'" + self.hostname + "'"
        print "\t\t'" + self.mac_vendor + "'"
        print "\t\t'" + self.ip + "'"
        print "\t\t'" + self.first_date + "'", str(self.time_since_first())[:-10]
        print "\t\t'" + self.last_date  + "'", str(self.time_since_first())[:-10]
        print "\t\t'" + 'First/Last Delta ' + "'", str(self.time_first_last())[:-10]

    def time_since_last(self):
        '''Return timedelta from last active till now'''
        return (datetime.datetime.now() - datetime.datetime.strptime(self.last_date, '%x %X'))

    def time_since_first(self):
        '''Return timedelta from first seen till now'''
        return (datetime.datetime.now() - datetime.datetime.strptime(self.first_date, '%x %X'))

    def time_first_last(self):
        '''Return timedelta from first seen till last seen'''
        return (datetime.datetime.strptime(self.last_date, '%x %X') - datetime.datetime.strptime(self.first_date, '%x %X'))

    def update(self, new_device_info):
        self.last_date = str(datetime.datetime.now())[:-10] # strip microseconds
        self.ip = new_device_info.ip

class Monitor_Devices():
    '''Track Device (by MAC Address) on your Network'''
    hosts = {'known':{}, 'unknown':{}, 'new':{} }  # Dict of 'mac':Device() ... {'known:{}, 'unknown':{}, 'new':{}}
    nmap_discovered_hosts = {}
    new_hosts = {}
    config_file = 'config.yml'
    known_hosts_file = 'known_hosts.yml'
    scan_frequency = 60
    ip_range = '192.168.0.0/24'

    def __init__(self):
        pass

    def __init__(self, config_file):
        '''Read and parse config file'''
        print "** Creating"

        # Get access_key, bucket_key, bucket_name from config
        with open(config_file, 'r') as readfile:
            config = yaml.load(readfile)

        if config['scan_frequency']:
            self.ip_range = config['ip_range']
        if config['scan_frequency']:
            self.scan_frequency = config['scan_frequency']


    def read_hosts_file(self):
        '''Get list of known/unknown MAC addresses'''

        with open(self.known_hosts_file, 'r') as readfile:
            self.hosts = {}  # Wipe old before refreshing
            self.hosts = yaml.safe_load(readfile)

            # If a certain required state isn't found, initialize to {} to avoid key errors later
            if not self.hosts:
                self.hosts = {}

            # Convert each Yaml string line to a Device
            for known_state in self.hosts:
                if self.hosts[known_state] == None: # If not "None"
                    self.hosts[known_state] = {}

                    for mac in self.hosts[known_state]:
                        self.hosts[known_state][mac] = Device(mac, self.hosts[known_state][mac])

            for known_state in ['known','unknown','new']:
                if  known_state not in self.hosts:
                    self.hosts[known_state] = {}

    def dump_hosts_file(self):
        temp = {}
        for known_state in self.hosts:
            temp[known_state] = {}
            for mac in self.hosts[known_state]:
                temp[known_state][mac] = self.hosts[known_state][mac].data()

        with open(hosts_file, 'w') as outfile:
            yaml.dump(temp, outfile, width=1000, default_flow_style=False)


    def print_specific_hosts(self, known_state='known', verbose=True, prepend="\t"):
        if not self.hosts[known_state]:
            print prepend, "No hosts"
            return

        for mac in self.hosts[known_state]:
            if verbose:
                print prepend, self.hosts[known_state][mac]
            else:
                print prepend, mac, host_dict[mac].hostname


    def print_hosts(self, known_state=None, verbose=True):
        '''Printing of specific or all hosts. Format: MAC: DETAIL_STRING'''
        if known_state:
            self.print_specific_hosts(known_state, verbose=verbose)
        else:
            for known_state in self.hosts:
                print known_state
                self.print_specific_hosts(known_state, verbose=verbose)

    def nmap_hosts(self):
        '''Nmap ping sweep defined IP Range, update last_date on known devices
            add any unknown devices'''
        macs_found = {}
        self.new_hosts = {}  # Wipe old before refreshing

        nmap = "nmap -sP  %s" % self.ip_range
        args = shlex.split(nmap)
        debug("Running: %s" % args)
        nmap_output = subprocess.check_output(args, shell=True)
        split_text = nmap_output.split('Nmap scan report for ')[1:]

        for line in split_text:
            #print line
            (ip, hostname, mac, mac_vendor) = ('','','','')
            # Nmap scan report for 192.168.1.13\n Host is up (0.034s latency).\n MAC Address: 60:38:E0:62:40:95 (Unknown)

            # This will match if NMAP is able to discover a hostname ... if not then next match will fire
            match = re.search(r"^([^\d].*)\((\d+\.\d+\.\d+\.\d+)\).*MAC Address: ([\dA-Fa-f:]+) \((.*)\)", line, re.DOTALL)
            if match:
                (hostname, ip,mac, mac_vendor) = match.group(1,2,3,4)
                #macs_found[mac] =  '%s | %s | %s | %s | %s' % (hostname, mac_vendor, ip, time.strftime("%c"), time.strftime("%c"))

            # This will match if no hostname found in NMAP, it starts with IP
            match = re.search(r"^(\d+\.\d+\.\d+\.\d+).*MAC Address: ([\dA-Fa-f:]+) \((.*)\)", line, re.DOTALL)
            if match:
                (ip, mac, mac_vendor) = match.group(1,2,3)
                #macs_found[mac] =  ' | %s  | %s | %s | %s' % (mac_vendor, ip, time.strftime("%c"), time.strftime("%c") )
                #self.nmap_discovered_hosts[mac] = Device(mac, macs_found[mac])

            if mac:     # If we matched the line and have info
                detail_string =  '%s | %s | %s | %s | %s' % (hostname, mac_vendor, ip, str(datetime.datetime.now())[:-10], str(datetime.datetime.now())[:-10])
                macs_found[mac] = detail_string
                new_device = Device(mac, detail_string)
                self.nmap_discovered_hosts[mac] = new_device

                found = False
                # If known then update IP/last_date ... else add to known and new list
                for known_state in self.hosts:
                    if mac in self.hosts[known_state]:
                        self.hosts[known_state][mac].update(new_device)
                        found = True

                if not found:
                    self.hosts['new'][mac] = new_device
                    self.hosts['unknown'][mac] = new_device


# TODO nmap should update known last timestamps
# TODO write out yaml file

if __name__ == '__main__':
    monitor = Monitor_Devices('config.yml')
    monitor.read_hosts_file()
    print "Known Hosts:"
    monitor.print_hosts(known_state='known')

    # for h in monitor.known_hosts:
    #     monitor.known_hosts[h].print_verbose()
    #
    # exit()

    monitor.nmap_hosts()
    print "NMAP Hosts:"
    monitor.print_hosts(known_state='new')
    monitor.dump_hosts_file()
    #print "NEW MACS: ", monitor.new_hosts()




    exit()
    try:
        while True:
            # Perform NMAP ping sweep to find active hosts/macs
            macs_found = find_active_macs(cfg['ip_range'])

            # Read in known/unknown MACs from file
            hosts = read_hosts_file(hosts_file)
            print "Found %d active MACs" % len(macs_found)

            for mac in macs_found:
                if mac in hosts['known']:
                    debug("Known : "+ mac)
                    # update last seen date


                else:
                    # MAC is not listed in known_hosts.yml under "known"

                    if 'unknown' not in  hosts or not hosts['unknown']: # initialize if not present (ugly!)
                        hosts['unknown'] = {}

                    if mac in hosts['unknown']:
                        # MAC is unknown (unlabled in known_hosts.yml) but has been unknown before
                        print "unknown :    ", mac
                    else:
                        desc = mac + ' | ' + macs_found[mac]
                        print "Unknown : %s" % (desc)
                        telegrambot.send_to_telegram(desc, cfg['telegram_token'], cfg['telegram_chat_id'])
                        hosts['unknown'][mac] = macs_found[mac]

                    write_yaml_hosts(hosts, hosts_file)

            # Wait 30 seconds between scans
            sleep(cfg['scan_frequency'])

    except KeyboardInterrupt:
        # On a keyboard interrupt signal threads to exit
        write_yaml_hosts(hosts, hosts_file)
