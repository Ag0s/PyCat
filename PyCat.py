#!/usr/bin/env python
#
#  PyCat - The Python NetCat Project v0.4
#
#  Works best with Python 2.x
#  Updated to work with Python 3.x
#
#  Required non default packages: pexpect (for ssl), netaddr (for windows)
#
#  Possible additions:
#      - [0%] Deamon for incomming connections, forking childs
#      - [100%] [Untested] Deamon to handle SSL
#      - [100%] [Untested] Outgoing SSL connection support
#      - [100%] [Untested] udp traffic

import sys
import ssl
import socket
import getopt
import threading
import subprocess

from netaddr import IPNetwork, IPAddress
from ctypes import *

# Global Variables
subnet = "192.168.0.0/24"
listen = False
command = False
upload = False
ssl = False
udp = False
execute = ""
target = ""
upload_dest = ""
port = 0
cert = ""
chat = False
chatserv = False
host = "0.0.0.0"


def usage():
    print "PyCat - The Secure Python NetCat Project"
    print
    print "Usage: pycat.py -t target_host -p port"
    print "-l --listen                - listen on [host]:[port] for incoming connections"
    print "-e --execute=/file/to/run   - execute the given file upon receiving a connection"
    print "-c --command               - initialize a command shell"
    print "-u --upload=destination    - upon receiving connection upload a file and write to [destination]"
    print "-s --ssl[=certificate]     - connect to a SSL secured port"
    print "-d --udp                   - use UDP port"
    print
    print "Examples: "
    print "pycat.py -t 192.168.0.1 -p 5555 -l -c"
    print "pycat.py -t 192.168.0.1 -p 5555 -l -u=c:\\\\folder\\\\target.exe"
    print "pycat.py -t 192.168.0.1 -p 5555 -s -e=\"cat /etc/passwd\""
    print "echo 'ABCDEFG' | ./pycat.py -t 192.168.0.1 -p 135"
    print
    sys.exit(0)

    
def scan():
    # ASCII Logo
    print '8888888b.          .d8888b.          888     '
    print '888   Y88b        d88P  Y88b         888     '
    print '888    888        888    888         888     '
    print '888   d88P888  888888         8888b.  888888 '
    print '8888888P" 888  888888           "88b8 88     '
    print '888       888  888888    888. d888888 888    '
    print '888       Y88b 888Y88b  d88P 888  888 Y88b.  '
    print '888        "Y88888 "Y8888P"  "Y888888  "Y888 '
    print '               888                           '
    print '          Y8b d88P                           '
    print '           "Y88P"                            '
    # ASCII Logo End
    print
    try:
        import scanner
    except ImportError:
        usage()
        sys.exit(0)
    print "[+]Scanning the pre-configured network."
    run = scanner.Scan()
    run
    print "[+]Scanning completed."


def create_cert():
    global cert
    
    print "No certificate found.\n"
    
    try: 
        import pexpect
    except ImportError:
        print "[*] No pexpect module found.\n"
        answer = raw_input("Would you like to try and install it? [Y/N]: ")
        
        if answer in ('Y', 'y', 'yes', 'Yes'):
            os.system('pip install pexpect')
        else:
            print "[*] Unable to install pexpect.\nPlease create a certificate manually."
            sys.exit(0)
    
    print "Creating certificate...\n"
    private_key = raw_input("Input certificate password: ")
    
    child = pexpect.spawn('openssl genrsa -des3 -out server.key 1024')
    child.expect('Enter pass phrase for server.key:')
    child.sendline (private_key)
    child.expect('Verifying - Enter pass phrase for server.key:')
    child.sendline(private_key)
    child = pexpect.spawn ('openssl req -new -key server.key -out server.csr')
    child.expect('Enter pass phrase for server.key:')
    child.sendline(private_key)
    child.expect('Country Name .*')
    child.sendline('')
    child.expect('State or Province Name')
    child.sendline('')
    child.expect('Locality Name')
    child.sendline('')
    child.expect('Organization Name')
    child.sendline('')
    child.expect('Organizational Unit')
    child.sendline('')
    child.expect('Common Name')
    child.sendline('')
    child.expect('Email Address')
    child.sendline('')
    child.expect('A challenge password')
    child.sendline('')
    child.expect('An optional company name')
    child.sendline('')
    child = pexpect.spawn('openssl x509 -req -days 3650 -in server.csr -signkey server.key -out server.crt')
    child.expect('Enter pass phrase for server.key:')
    child.sendline(private_key)
    os.system('cp server.key server.key.secure')
    child = pexpect.spawn('openssl rsa -in server.key.secure -out server.key')
    child.expect('Enter pass phrase for .*:')
    child.sendline(private_key)
    
    cert = "server.crt"

    
def client_sender(buffer):
    global ssl
    global udp

    # Try to determine connection type
    try:
        if ssl and not udp:
            # Try to setup SSL encrypted connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # init.settimeout(10)
            client = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv2, ciphers="ADH-AES256-SHA")
            client.connect((target, port))

        elif udp and not ssl:
            if upload:
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            else:
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client.sendto(snd_buffer, (target_host, target_port))
        else:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((target, port))

        if len(buffer):
            client.send(buffer)
            while True:
                recv_len = 1
                rsponse = ""

                while recv_len:
                    data = client.recv(4096)
                    recv_len = len(data)
                    response += data

                    if recv_len < 4096:
                        break

                print response,

                buffer = raw_input("")
                buffer += "\n"

                if udp:
                    client.sendto(buffer, (target, port))
                else:
                    client.send(buffer)

    except:
        print "Unhandled Exception - 0x0003 client_sender"
        # Close connection
        client.close()


def server_loop():
    global target
    global ssl
    global cert
    
    # If no target is specified, listen on all interfaces
    if not len(target):
        target = "0.0.0.0"
        
        if len(cert) == 0:
            create_cert()
        
        if ssl:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server = ssl.wrap_socket(sock, server_side=True, ca_certs=cert, keyfile=cert.rsplit( ".", 1 )[ 0 ]+".key")
                server.bind((target, port))
                server.listen(5)
        
            except:
                print "[*] Invalid certificate or key file.\nCertificate and key files must be in the same folder and have the same name."
                sys.exit(0)
        
        else:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((target, port))
            server.listen(5)

        while True:
            client_socket, addr = server.accept()

            # Spin off a thread to handle new client
            client_thread = threading, Thread(target=client_handler, args=(client_socket,))
            client_thread.start()


def run_command(command):
    # Trim the new line
    command = command.rstrip()

    # Run command and retrieve output
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except:
        output = "Failed to execute command.\r\n"

    # Send output back to client
    return output


def prompt() :
    sys.stdout.write('<You>: ')
    sys.stdout.flush()

    
def client_handler(client_socket):
    global upload
    global execute
    global command
    global ssl
    global chat

    # Check for upload
    if len(upload_dest):
        # Read in all of the bytes and write to out destination
        file_buffer = ""

        # Keep reading data until none is available
        while True:
            data = client_socket.recv(1024)

            if not data:
                break
            else:
                file_buffer += data

        # Try to write bytes
        try:
            file_descriptor = open(upload_dest, "wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()

            # Confirm that we wrote the file
            client_socket.send("Successfully saved file to {}\r\n".format(upload_dest))
        except: 
            client_socket.send("Failed to save file to {}\r\n".format(upload_destination))

    if len(execute):
        # Run the command
        output = run_command(execute)

        client_socket.send(output)

    # Start another loop if command shell was requested
    if command:
        while True:
            # Show prompt
            client_socket.send("pycat:{}:$ ".format(target))

            # Receive until line feed has been given (enter key)
            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024)

            # Send back the command output
            response = run_command(cmd_buffer)

            # Send the response back
            client_socket.send(response)

    else:
        print "Unhandled Exception - 0x0002 client_handler"


# Main function
def main():
    global listen
    global port
    global execute
    global command
    global ssl
    global upload_dest
    global target
    global chat

    # Check if arguments are passed, if not start scan
    if not len(sys.argv[1:]):
        scan()

    # Read the options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:s:d:cu:", ["help", "listen", "execute", "target", "port", "ssl", "udp", "command", "upload"])

    except getopt, GetoptError:
        print str(sys.exc_info())
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command"):
            command = True
        elif o in ("-u", "--upload"):
            upload = True
            upload_dest = a
        elif o in ("-t", "--target"):
            target = str(a)
        elif o in ("-p", "--port"):
            port = int(a)
        elif o in ("-s", "--ssl") and o not in ("-d", "--udp"):
            ssl = True
            cert = a
        elif o in ("-d", "--udp") and o not in ("-s", "--ssl"):
            udp = True
        else:
            assert False, "Unhandled Option"

    # Are we going to listen or just send data from stdin?
    if command:
        if len(target) and port > 0:

            # Read in the buffer from the commandline, this will block, so send CTRL-D
            # if not sending input to stdin
            buffer = sys.stdin.read("Input command: ")

            # Send data off
            client_sender(buffer)
        else:
            print "[!] No target or port supplied"

    # We are going to listen and potentially upload things, execute commands and drop a shell back
    # depending on the above commandline options
    elif listen:
        server_loop()

    elif chat:
        chat_client()

    else:
        print "Unhandled Exception - 0x0001 main"

main()
