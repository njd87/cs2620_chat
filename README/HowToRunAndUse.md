# What is this project

This is a live chat application built for Harvard's CS 2620. It is programmed to run a single server that can connect to multiple clients and communicate to a database based on those interactions.

# How to run
This program was built for Python 3.10.x and above. It uses all built-in libraries, so no requirements.txt necessary.

First, you'll need to setup the database by running:

```bash
python setup.py
```

Next, you will want to run the server. This can be done by simply running:

```bash
python server.py
```

The host, port, and protocol are set for you in the config/config.json file.

To run a client, simply run:

```bash
python3 client.py <HOST> <PORT>
```

By default, these params are 127.0.0.1 and 65432, so if left unchanged, you can use as default:

```bash
python3 client.py 127.0.0.1 65432
```


Use the Host and Port numbers provided in the server config.

# Using the Client UI
When first opened, you will be prompted to enter a username.

If it exists, you will be prompted to login. If not, you will be prompted to register.
If you received messages while you were offline, you will also be prompted to select how many messages you would like to read before logging back in.

NOTE: Sometimes, tkiner can take a little bit (~3-5 seconds) to correctly render entry boxes. To speed this up, you can click on the entry box. In addition, sometimes buttons are a bit finicky, but this has always been a commonplace with tkinter in python.

Once you are logged in on the home page, select any of the people on the left hand side and click "message" to start messaging them. Use the window on the right to send messages. You can select messages you have sent and delete them.
You will also be pinged from other people you are currently not messaging.

Clicking "settings" will allow you to delete your account. Follow the instructions to delete the account. Once your account is deleted, recipients of your text messages will no longer be able to view your messages.