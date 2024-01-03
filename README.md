## Simple botnet using dropbox for communication

Unfortunately, due to the limited time I've had for this assignment, I didn't manage to iron out some of the wrinkles of the application. It does, however, satisfy the given requirements. Please be patient with the UI (sometimes the commands "don't register" and need to be repeated, I'm sorry about the inconvenience).
### Communication

Communication is done via embedding simple commands in images using steganography. The images are generated using https://pypi.org/project/randimage/ and are randomly named a given list. The commands consist of fields separated by a pipe symbol and the individual commands are separated by a semicolon.
The structure can be seen below:
`timestamp|(REQUEST or RESPONSE)|command|content;`
Example:
`03/01/2024 18:12:32|REQUEST|who|;`


### Set up
1) install requirements.txt
2) create an application in dropbox and generate an access token for it
3) run python scripts

note: for the first time the server should be executed before any clients because it uploads a list of possible names for the clients to the dropbox, afterwards the order of execution of server/client does not matter 

### Scripts Usage
Both scripts require arguments to work properly:
`python3 ./client.py $ACCESS_TOKEN $TMP_DIR`
`python3 ./server.py $ACCESS_TOKEN $TMP_DIR $BCKUP_DIR`

- `$ACCESS_TOKEN` - your dropbox application access token
- `$TMP_DIR` - path to directory where images/commands are downloaded from dropbox (please include / at the end of the path e.g. /tmp/ not /tmp)
- `$BCKUP_DIR` - path to directory where files from clients are downloaded and communication with clients is saved upon breaking contact (please include / at the end of the path e.g. /bckp/ not /bckp)

Example: `python3 ./server.py foo ./tmp/ ./backup/`

### Features
- `w` command
- `ls $DIR` command, dir is the path to the directory on the client machine
- `id` command
- `cp $FILE_PATH` copy file at the given path on the client machine to the `$BCKUP_DIR` on the server machine
- `$BIN_PATH` execute binary file located at a given path
- personalized one-to-one communication and broadcasting of commands
- simple command line UI
- saving of the communication with a client on client timeout or on server exit to `$BCKUP_DIR`

note: additional configuration of timeouts might be done by modifying constants at the start of each script
