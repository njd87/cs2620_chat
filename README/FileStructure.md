# How is this project organized

## Server and Client

The chat application has two main types of actors: the server and the client.

At a single time, only one server is run, listening on a given host and port (specified in config). Multiple clients may then be accepted onto this server. Servers are run via "server.py" and clients are run via "client.py".

Both the server and the client run main "event loops" where they are constantly looking for responses and requests so that, when such an action is made, the respective listener may take action.

## comm_client and comm_server
Connections are made on sockets and events are announced via selectors. However, much of the lower-level communication between sockets is made through what we called " Bidreictional Object Logging Transmitters" or BOLTs. There are two types of Bolt: server-side and client-side. The documentation for these are in comm_server.py and comm_client.py (this are not main scripts and only include the Bolt class).

Server-side bolts listen for requests, process them over the socket, prepare a response, and transfer the response to the client-side bolt. The client-side bolt then translates the response and prepares a request back. In short, it is the medium in which the server and client are able to read and write on the sockets.

## Protocols
The method in which responses and requests are transferred over the wire is meant to be pre-specified in the config file. Both the client and the server should have the same protocol, else the connection will close due to a mismatch.

'json' is the default protocol and utilizes the built-in encoder/decoder of the json library to transfer information stored in json objects over the socket in bytes.

'custom' is our pre-built protocol that does custom recursive parsing via functions in "parse_helpers.py" to send nested built-in python dictionaries over the wire via string encoding/decoding.

## Unit Testing

Finally, we developed a test suite using the unittest library.

These unittests test the backend logic for both of our protocols, as well as custom helper functions we designed in parse_helpers. The tests simulate multiple users interacting over a wire to the same server conducting each possible action available:
- check_username (checking availability of username)
- login (logging in the user)
- register (registering the user)
- load_chat (loading the messages between two users)
- send_message (sending message from sender to recipient)
- ping (notify online users)
- view_undelivered (view new messages when logging in)
- delete_message (deleting sent messages)
- delete_account (deleting account)
- ping_user (notify of new users)

And making sure the database responds in the correct way.