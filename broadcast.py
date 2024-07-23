'''
Date: 2024-07-17 13:14:45
Author: DarkskyX15
LastEditTime: 2024-07-18 17:31:22
'''

from threading import Thread
from queue import Queue, Empty
from socket import *
from random import randint
from tool import SimplePacket
from typing import Any

__all__ = ['BroadcastServer', 'BroadcastClient']

BROADCAST_MSG = 'fileThrower bRoadcast.'

class BroadcastServer:
    broadcast_address: tuple[str, int]
    broadcast_socket: socket
    recv_port: int
    recv_thread : Thread
    bc_sign: str
    msg_queue: Queue
    def __init__(self, broadcast_addr: tuple[str, int],
                 recv_addr: tuple[str, int],
                 match_key: str,
                 broadcast_sign: str = BROADCAST_MSG) -> None:
        self.bc_sign = broadcast_sign
        self.recv_port = recv_addr[1]
        self.broadcast_address = broadcast_addr
        self.broadcast_socket = socket(AF_INET, SOCK_DGRAM)
        self.broadcast_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        self.broadcast_socket.bind((recv_addr[0], randint(30000, 60000)))
        self.msg_queue = Queue()
        self.recv_thread = Thread(target=BroadcastServer._recv_thread,
                                  args=(self.recv_port, self.msg_queue, match_key, recv_addr[0]))

    @staticmethod
    def _recv_thread(recv_port: int, msg_q: Queue, match_key: str, local_ip: str) -> None:
        recv_socket = socket(AF_INET, SOCK_DGRAM)
        recv_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        recv_socket.bind((local_ip, recv_port))
        while True:
            data, address = recv_socket.recvfrom(1024)
            sp_bag = SimplePacket.decode(data)
            if sp_bag is not None:
                if sp_bag.get('key', None) == match_key:
                    sp_bag['addr_ip'] = address[0]
                    sp_bag['addr_port'] = address[1]
                    msg_q.put(sp_bag)
                    recv_socket.close()
                    break

    def run_till_recv(self) -> dict[str, Any]:
        self.recv_thread.start()
        while True:
            self.broadcast_socket.sendto(SimplePacket.encode({
                "msg": self.bc_sign, 
                "port": self.recv_port
            }), self.broadcast_address)
            try:
                ret_msg = self.msg_queue.get(block=True, timeout=1.5)
                self.broadcast_socket.close()
                return ret_msg
            except Empty:
                pass

class BroadcastClient:
    recv_socket: socket
    match_key: str
    bc_sign: str
    def __init__(self, bind_addr: tuple[str, int], match_key: str,
                 broadcast_sign: str = BROADCAST_MSG, timeout: float = None) -> None:
        self.bc_sign = broadcast_sign
        self.recv_socket = socket(AF_INET, SOCK_DGRAM)
        self.recv_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        self.recv_socket.settimeout(timeout)
        self.recv_socket.bind(bind_addr)
        self.match_key = match_key
    
    def run(self, fellow_port: int) -> str:
        addr: tuple[str, int]
        while True:
            data, addr = self.recv_socket.recvfrom(1024)
            sp_bag = SimplePacket.decode(data)
            if sp_bag is not None:
                remote_recv_port = sp_bag.get("port", 0)
                if remote_recv_port <= 0: continue
                if sp_bag.get("msg", '') == self.bc_sign:
                    break
        self.recv_socket.close()
        send_socket = socket(AF_INET, SOCK_DGRAM)
        send_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        send_socket.sendto(SimplePacket.encode({
            "key": self.match_key,
            "port": fellow_port
        }), (addr[0], remote_recv_port))
        send_socket.close()
        return addr[0]