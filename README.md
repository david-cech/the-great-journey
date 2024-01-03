## Simple botnet using dropbox for communication

Unfortunately, due to the limited time I've had for this assignment, I didn't manage to iron out some of the wrinkles of the application. It does, however, satisfy the given requirements.
### Communication

Communication is done via embedding simple commands in images using steganography. The images are generated using https://pypi.org/project/randimage/ and are named at random from a list. The commands consist of fields separated by a pipe symbol and the individual commands are separated by a semicolon. Example can be seen below:
`timestamp|(REQUEST or RESPONSE)|command|content;`
Example:
`03/01/2024 18:12:32|REQUEST|who|;`


### Set up
1) install requirements.txt
2) create an application in dropbox and generate an access token for it
3) run python scripts

### Scripts Usage
Both scripts require arguments to work properly:
`python3 ./client.py $ACCESS_TOKEN $TMP_DIR`
`python3 ./server.py $ACCESS_TOKEN $TMP_DIR $BCKUP_DIR`

- `$ACCESS_TOKEN` - your dropbox application access token
- `$TMP_DIR` - path to directory where images/commands are downloaded from dropbox (please include / at the end of the path e.g. /tmp/ not /tmp)
- `$BCKUP_DIR` - path to directory where files from clients are downloaded and communication with clients is saved upon breaking contact (please include / at the end of the path e.g. /bckp/ not /bckp)

### Features
- `w` command
- `ls $DIR` command
- `id` command
- `cp $FILE_PATH` copy file at the given path on the client machine to the `$BCKUP_DIR` on the server machine
- `$BIN_PATH` execute binary file located at a given path
- personalized communication and broadcast of commands
- simple command line UI
- saving of the communication with a client on client timeout or on server exit 

note: additional configuration of timeouts might be done by modifying constants at the start of each script