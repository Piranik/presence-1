This project is really two main components: 1) Ping sweep detection of new Hosts on your network and 2) Telegram notification bot to let you know a new host appeared ASAP.

Ping sweep (NMAP) local network keeping track of known hosts based on MAC. When a new MAC addresses is detected, log the IP/MAC and MAC Vendor to YAML file and notify me via Telegram bot.

When admin receives a text message he can reply to the Bot to give that new host a proper name. The thought is that you receive the update in near real-time and you know who/what was just plugged or Wifi attached to your network so you name it right away.

TODO:
* Telegram bot will allow Admin to Block (future) that MAC via Firewall rule
* Log and visually graph when hosts are online vs offline historically
* possible notifications if 'required' hosts aren't online
* Set temporary notifications when a device comes/goes (good for iPhone/person presence tracking)
* add additional methods to detect via Bluetooth and sniff wifi for devices that are close but not attached to your network
