import dropbox
import sys
import os
from stegano import lsb

def init(access_token):
    access_token = sys.argv[1]
    dbx = dropbox.Dropbox(access_token)

    if len(dbx.files_list_folder('').entries) == 0:
        dbx.files_create_folder('/art')

    for entry in dbx.files_list_folder('').entries:
        print(entry.name)

    return dbx


def get_user_id():
    return str(os.getuid())


def list_dir(path):
    ret = ""
    for name in os.listdir(path):
        ret+= name+'\n'
    return ret


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Error - Invalid Call")
        print("Usage: python3", sys.argv[0], "APP_ACCESS_TOKEN")
    else:
        #dbx = init(sys.argv[1])
        #secret = lsb.hide("./cute_in.png", "Hello world!\n",  lsb.generators.eratosthenes())
        #secret.save("./cute_out.png")
        print("placeholder")