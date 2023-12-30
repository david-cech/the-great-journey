import dropbox
import sys
from stegano import lsb
from randimage import get_random_image
import matplotlib
import random

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


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Error - Invalid Call")
        print("Usage: python3", sys.argv[0], "APP_ACCESS_TOKEN")
    else:
        dbx = init(sys.argv[1])
        message = lsb.reveal("./cute_out.png", lsb.generators.eratosthenes())
        register(dbx)
        #print(message)