# Spartan-Messenger
Spartan Messenger using GRPC in Python3 is a console group chat application. Used gRPC response streaming to continuously receive chat messages from the Spartan server.

# Steps to execute the code
- Run charServer.py and pass port number as an input
- Run multiple charClient.py and pass port number as an input
- Start chatting

# Execute in this order
- python3 charServer.py 3000
- python3 chatClient.py 3001
- python3 chatClient.py 3002
- python3 chatClient.py 3003
