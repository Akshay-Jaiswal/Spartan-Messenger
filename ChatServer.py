from concurrent import futures
# from LRUCache import LRUCache
import grpc
import yaml
import io
import chat_pb2 as chat_pb2
import chat_pb2_grpc as chat_pb2_grpc

import chardet
import time
import collections

# from decorator import rate
from decorator import lru

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Chat(chat_pb2_grpc.ChatServicer):

    def __init__(self, port: str, users: list, group1: list, group2: list, key: str, cachesize):
        self.group_1_lastIndex = 0
        self.group_2_lastIndex = 0
        self.group_lastIndex = 0
        self.chat_record = []
        self.name = 'Spartan server'
        self.port = port
        self.users = users
        self.group1 = group1
        self.group2 = group2
        self.key = key.encode('utf-8')
        self.welcomeMessage1 = 'Connected to Spartan Server at port '+str(self.port)+'.'
        self.group_1_user_list = ','.join(self.group1)
        self.group_2_user_list = ','.join(self.group2)

        self.clienttimedictionary = collections.OrderedDict()
        self.group_1_cache = collections.OrderedDict()
        self.group_2_cache = collections.OrderedDict()
        # self.cache_group_1 = LRUCache(int(cachesize))
        # self.cache_group_2 = LRUCache(int(cachesize))

        self.encryption_suite = AES.new(self.key, AES.MODE_ECB)
        self.decryption_suite = AES.new(self.key, AES.MODE_ECB)

    def welcome_message_generator(self, request):

        if request.name in self.group1:
            welcomeMessage2 = "User list : "+','.join(self.group1)
        else:
            welcomeMessage2 = "User list : "+','.join(self.group2)

        welcome_message_list = [self.welcomeMessage1, welcomeMessage2]
        return welcome_message_list

    def loginToChat(self, request: chat_pb2.ClientInfo, context):

        if str(request.name) in self.users:
            welcome_message = self.welcome_message_generator(request)
            for i in range(2):
                # print("i = "+str(i))
                # print("welcome message = "+welcome_message[i])
                reply = chat_pb2.LoginStatus(name=self.name, status=True, welcome_message=welcome_message[i])
                yield reply
        else:
            return chat_pb2.LoginStatus(status=False)

    def sendMessage(self, request: chat_pb2.OutgoingMessage, context):

        if self.decryptString(request.name) in self.group1:
            self.group_1_cache = self.add_to_lru_cache(request, self.group_1_cache)
            self.group_1_lastIndex = list(self.group_1_cache.keys())[-1]+1
        else:
            self.group_2_cache = self.add_to_lru_cache(request, self.group_2_cache)
            self.group_2_lastIndex = list(self.group_2_cache.keys())[-1]+1

        return chat_pb2.Empty()

    def waitForMessage(self, request, context):
        if request.name in self.group1:
            if len(self.group_1_cache) == 0:
                lastIndex1 = 0
            else:
                lastIndex1 = list(self.group_1_cache.keys())[0]
            while True:
                while self.group_1_lastIndex > lastIndex1:
                    n = self.group_1_cache[lastIndex1]
                    lastIndex1 += 1
                    yield n
        else:
            if len(self.group_2_cache) == 0:
                lastIndex1 = 0
            else:
                lastIndex1 = list(self.group_2_cache.keys())[0]

            while True:
                while self.group_2_lastIndex > lastIndex1:
                    n = self.group_2_cache[lastIndex1]
                    lastIndex1 += 1
                    yield n

    def ratelimit(func):
        def wrapper(*args, **kwargs):
            wrapper_self = args[0]
            wrapper_request = args[1]
            wrapper_group_cache = args[2]
            clientname = wrapper_self.decryptString(wrapper_request.name)
            if len(wrapper_self.clienttimedictionary.setdefault(clientname, [])) < 3:
                    wrapper_self.clienttimedictionary[clientname].append(time.time())
                    return func(*args, **kwargs)
            else:
                if (time.time() - wrapper_self.clienttimedictionary.get(clientname)[0]) < 30:
                    return wrapper_group_cache

                else:
                    wrapper_self.clienttimedictionary[clientname].pop(0)
                    wrapper_self.clienttimedictionary[clientname].append(time.time())
                    return func(*args, **kwargs)

        return wrapper


    @ratelimit
    @lru
    def add_to_lru_cache(self, request, group_cache):
        # print("[{}] {}".format(request.name, request.outgoingMsg))
        if len(group_cache) == 0:
            group_cache[0] = request
        else:
            group_cache[list(group_cache)[-1]+1] = request
        return group_cache


    def encryptString(self, inputString):
        inputString = bytes(self.applyPadding(inputString).encode('utf-8'))
        return self.encryption_suite.encrypt(inputString)

    def decryptString(self, inputString):
        decryptedString = (self.decryption_suite.decrypt(inputString)).decode('utf-8')
        return self.removePadding(decryptedString)

    def applyPadding(self, inputString):
        inputString = inputString.ljust(len(inputString)+16 - (len(inputString) % 16), ' ')
        return inputString

    def removePadding(self, inputString):
        inputString = inputString.rstrip()
        return inputString

def serve():
    with open("config.yaml", 'r') as stream:
        data_loaded = yaml.load(stream)
        # print("Spartan server side port is : "+str(data_loaded.get('port')))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServicer_to_server(Chat(str(data_loaded.get('port')), data_loaded.get('users'), data_loaded.get('groups')['group1'], data_loaded.get('groups')['group2'], str(data_loaded.get('encryptionkey')), str(data_loaded.get('max_num_messages_per_user'))), server)
    server.add_insecure_port('[::]:'+str(data_loaded.get('port')))
    server.start()
    print("Spartan server started at port : "+str(data_loaded.get('port')))
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
