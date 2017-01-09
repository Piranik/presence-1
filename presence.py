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
#re_date = re.compile(r"")

logging.basicConfig(stream=sys.stderr, level=log_level)

# Get access_key, bucket_key, bucket_name from config
with open(config_file, 'r') as readfile:
    cfg = yaml.load(readfile)

# Error check config
# TODO: scan_frequency must be present and integer


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
        temp = map(str.strip, device_string.split('|')) # Remove trailing spaces
        temp = map(str.lstrip, temp)    # Remove leading spaces
        (self.hostname, self.mac_vendor, self.ip, self.first_date, self.last_date) = temp

    # def __init__(self, mac, hostname, mac_vendor, ip):
    #     self.hostname = hostname
    #     self.mac = mac
    #     self.mac_vendor = mac_vendor
    #     self.ip = ip

    def __str__(self):
        arr = [self.hostname, self.mac_vendor, self.ip, str(self.first_date), str(self.last_date)]
        return '|'.join(arr)

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
        self.last_date = str(datetime.datetime.now())[:-7] # strip microseconds
        self.ip = new_device_info.ip



class Monitor_Devices():
    '''Track Device (by MAC Address) on your Network'''
    known_hosts = {}  # Dict of 'mac':Device()
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
            self.known_hosts = {}  # Wipe old before refreshing
            hosts = yaml.safe_load(readfile)

            try:
                for mac in hosts['known']:
                    #print mac, hosts['known'][mac]
                    self.known_hosts[mac] = Device(mac, hosts['known'][mac])
            except Exception as e:
                print "Error: Maybe no 'known' hosts in file? ", e
                pass

            try:
                for mac in hosts['unknown']:
                    self.known_hosts[mac] = Device(mac, hosts['unknown'][mac])
            except:
                print "Error: Maybe no 'unknown' hosts in file?"
                pass

    def dump_hosts_file(self):
        temp = {}
        for mac in self.known_hosts:
            temp[mac] = str(self.known_hosts[mac])

        # with open(hosts_file, 'w') as outfile:
        print yaml.dump(temp, width=1000, default_flow_style=False)


    def print_hosts(self, host_dict, prepend="\t"):
        '''Generic printing of MAC: DETAIL_STRING'''
        for mac in host_dict:
            print prepend, host_dict[mac]

    def print_hosts_brief(self, host_dict, prepend="\t"):
        for mac in host_dict:
            print prepend, mac, host_dict[mac].hostname

    def print_hosts_verbose(self, host_dict):
        for mac in host_dict:
            host_dict[mac].print_verbose()

    def print_known_hosts(self):
        self.print_hosts(self.known_hosts)

    def print_nmap_hosts(self):
        self.print_hosts(self.nmap_discovered_hosts)


    def nmap_hosts(self):
        macs_found = {}

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
                detail_string =  '%s | %s | %s | %s | %s' % (hostname, mac_vendor, ip, time.strftime("%c"), time.strftime("%c"))
                macs_found[mac] = detail_string
                self.nmap_discovered_hosts[mac] = Device(mac, detail_string)

                if mac not in self.known_hosts:
                    new_hosts[mac] = Device(mac, detail_string)
                else:
                    self.known_hosts[mac].update(Device(mac, detail_string))


# TODO nmap should update known last timestamps
# TODO write out yaml file

if __name__ == '__main__':
    monitor = Monitor_Devices('config.yml')
    monitor.read_hosts_file()
    print "Known Hosts:"
    monitor.print_known_hosts()

    for h in monitor.known_hosts:
        monitor.known_hosts[h].print_verbose()

    exit()
    monitor.nmap_hosts()
    print "NMAP Hosts:"
    monitor.print_nmap_hosts()

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
