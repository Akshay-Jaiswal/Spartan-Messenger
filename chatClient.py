from __future__ import print_function

import grpc
import sys
import threading

import chat_pb2
import chat_pb2_grpc as chat_pb2_grpc

import yaml
import io
import chardet
import time

# from decorator import rate
from Crypto.Cipher import AES


class ChatClient:

    def __init__(self, userName: str):
        self.userName = userName
        self.chat_record = []
        self.count = 0
        with open('config.yaml', 'r') as stream:
            data_loaded = yaml.load(stream)
            self.port = data_loaded.get('port')
            self.key = data_loaded.get('encryptionkey').encode('utf-8')
            self.rate = int(data_loaded.get('max_call_per_30_seconds_per_user'))

        self.encryption_suite = AES.new(self.key, AES.MODE_ECB)
        self.decryption_suite = AES.new(self.key, AES.MODE_ECB)
        self.encryptedUserName = self.encryptString(self.userName)

        with grpc.insecure_channel('127.0.0.1:'+str(self.port)) as channel:
            self.stub = chat_pb2_grpc.ChatStub(channel)
            if self.loginToChat():
                # print("login successful")
                threading.Thread(target=self.listenForMessage, daemon=True).start()
                while True:
                    self.sendMessage()
            else:
                print("Invalid user!!!")

    def loginToChat(self):
        response = self.stub.loginToChat(chat_pb2.ClientInfo(name=self.userName))
        login_status = False
        for msg in response:
            if bool(msg.status):
                print("[{}] > {} ".format(msg.name, msg.welcome_message))
                login_status = True
        return bool(login_status)

    def listenForMessage(self):
        response = self.stub.waitForMessage(chat_pb2.ClientInfo(name=self.userName))
        for msg in response:
            senderName = self.decryptString(msg.name)
            senderMsg = self.decryptString(msg.outgoingMsg)
            print("[{}] > {} ".format(senderName, senderMsg))
            self.chat_record.append("[{}] {}".format(senderName, senderMsg))

    def sendMessage(self):
        time.sleep(0.2)
        inputsting = str(input('[{}] '.format(self.userName)))
        encoded = self.encryptString(inputsting)

        if inputsting is not '':
            n = chat_pb2.OutgoingMessage()
            n.name = self.encryptedUserName
            n.outgoingMsg = encoded
            response = self.stub.sendMessage(n)

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


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print("Username is :"+str(sys.argv[1]))
        userName = str(sys.argv[1])
        client = ChatClient(userName)
    else:
        pass

