import base64
import argparse
import textwrap
from scapy.all import *
from scapy.layers.dot11 import Dot11Elt

env = b"\x20"
power = b"\x17"
# Country code must match [CA] default
country = Dot11Elt(ID='Country', info=(b"CA" + env))
tim = Dot11Elt(ID='TIM', info=b'\x00\x01\x00\x00')

def xor_encrypt(text, key):
    return ''.join([chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(text)])

def create_ssid(command, key):
    encrypted = xor_encrypt(command, key)
    b64 = base64.b64encode(encrypted.encode()).decode()
    return "Subrosa-" + b64

def start_ap(ssid, iface):
    from scapy.layers.dot11 import Dot11, Dot11Beacon
    dot11 = Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff",
                  addr2=RandMAC(), addr3=RandMAC())
    beacon = Dot11Beacon(cap="ESS")
    essid = Dot11Elt(ID="SSID", info=ssid)
    rsn = Dot11Elt(ID='RSNinfo', info=(
        b'\x01\x00'              # RSN Version 1
        b'\x00\x0f\xac\x02'      # Group Cipher Suite : 00-0f-ac TKIP
        b'\x02\x00'              # 2 Pairwise Cipher Suites
        b'\x00\x0f\xac\x04'      # AES Cipher
        b'\x00\x0f\xac\x02'      # TKIP Cipher
        b'\x01\x00'              # 1 Authentication Key Management Suite
        b'\x00\x0f\xac\x02'      # Pre-Shared Key
        b'\x00\x00'              # RSN Capabilities
    ))

    from scapy.layers.dot11 import RadioTap
    frame = RadioTap()/dot11/beacon/essid/rsn/country/tim

    print(f"[+] Broadcasting wake_up Payload: {ssid}")
    sendp(frame, iface=iface, inter=0.1, loop=1, verbose=0)

def stop_ap(ssid, iface):
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='duckrosa_wake_up.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
        Subrosa Wake Up
        -----------------------
        Sends XOR + Base64 encrypted command payloads over WiFi SSID broadcasts.

        Commands:
            wake_up - Wakes up pico

        Example usage:
            sudo airmon-ng start wlo1
            sudo python3 duckrosa_wake_up.py -c "wake_up" -k "supersecret"
        """)
    )
    parser.add_argument("--command", "-c", help="Payload to send (e.g., wake_up)", required=True)
    parser.add_argument("--iface", "-i", help="Wireless interface in monitor mode", default="wlo1mon")
    parser.add_argument("--key", "-k", help="XOR key to be used for encryption", default="secretkey")
    args = parser.parse_args()

    ssid = create_ssid(args.command, args.key)
    print("[+] SSID:", ssid)
    start_ap(ssid, args.iface)
