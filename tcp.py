
from logger import LoggerWrapper as _LogW
from typing import Literal as _Literal, Union as _Union, Any as _Any
from socket import socket as _socket
from base64 import b64decode as _b64de, b64encode as _b64en
from json import dumps as _dumps, loads as _loads
from pickle import loads as _ploads, dumps as _pdumps

__all__ = ['Packer', 'PacketError', 'Coder',
           'SM_JSON', 'SM_PICKLE', 'SM_RAW']

SM_JSON = 0
SM_PICKLE = 1
SM_RAW = 2

class PacketError(Exception):
    r'''在`Packer`类的方法执行过程中遇错误默认抛出的错误类型'''
    def __init__(self, msg: str, args: tuple[object]) -> None:
        err_s = ', '.join([str(arg) for arg in args])
        self.e_str = msg + err_s
        super().__init__(self.e_str)
    def __str__(self) -> str:
        return self.e_str
    def __repr__(self) -> str:
        return self.e_str

class Coder:
    r'''
    Packer加密所用的加密器的基类, 默认进行base64加密.

    继承并重写其中的`encrypt`和`decrypt`方法来实现自定义的加密器.

    正确的`encrypt`和`decrypt`方法接受`data`和`key`, 返回加密或解密后的数据(以`bytes`的形式).

    重写`__init__`方法时必须指定属性`self.name`(以`str`类型指定加密器的名字), 否则遇异常处理会出现错误.
    '''
    name = 'Default'
    def __init__(self, *args) -> None:
        self.name = 'Default'

    def encrypt(self, data: bytes, key: bytes = None) -> _Union[bytes, None]:
        return _b64en(data)

    def decrypt(self, data: bytes, key: bytes = None) -> _Union[bytes, None]:
        return _b64de(data)

class Packer:
    r'''
    自定义的包装类, 一定程度上解决TCP的粘包问题.

    初始化参数说明:
    - `encoder`: 包装器所用的加密器对象
    - `error`: 错误处理类型(`loose`或`strict`)
    - `logger`: 可选传入的LoggerWrapper对象
    '''
    def __init__(self, encoder: Coder, error: _Literal['strict', 'loose'] = 'strict', logger: _LogW = None) -> None:
        self._encoder = encoder
        self._error: _Literal['strict', 'loose'] = error
        self._use_logger = False if logger == None else True
        self._logw = logger


    def sendPacket(self, client: _socket, obj: object, key: bytes = None,
                   serialization_method: int = SM_JSON) -> bool:
        r'''
        将`obj`通过`client`发送.
        参数说明:
        - `client`: TCP链接的`socket`对象
        - `obj`: 需要发送的对象
        - `key`: 加密时使用的密钥
        - `pickle`: 若为真，将`obj`序列化后发送，否则使用json转换对象
        '''
        if serialization_method == SM_RAW:
            send_data = obj
        elif serialization_method == SM_JSON:
            try: send_data = _dumps(obj).encode('utf-8')
            except Exception as e:
                if self._error == 'strict': raise PacketError('Fail JSON', e.args)
                else:
                    err = PacketError('Fail JSON', e.args)
                    if self._use_logger: self._logw.error(err)
                    else: print(err)
                return False
        else: send_data = _pdumps(obj, fix_imports = False)
        try: coded = self._encoder.encrypt(send_data, key)
        except Exception as e:
            e_str = f'Can not encode data with \'{self._encoder.name}\' while sending packet: '
            if self._error == 'strict': raise PacketError(e_str, e.args)
            else:
                e_str = '[TCPPacketErr]' + e_str
                err = PacketError(e_str, e.args)
                if self._use_logger: self._logw.error(err)
                else: print(err)
            return False
        
        if len(coded) >= 65536:
            e_str = f'Packet is too big: {len(coded)}Bytes'
            if self._error == 'strict': raise PacketError(e_str, ())
            else:
                e_str = '[TCPPacketErr]' + e_str
                err = PacketError(e_str, ())
                if self._use_logger: self._logw.error(err)
                else: print(err)
            return False

        try:
            pack_size = len(coded)
            pack_header = pack_size.to_bytes(2, 'big')
            client.sendall(pack_header)
            send_data_size = pack_size
            send_data_pointer = 0
            while True:
                if send_data_size <= 1024:
                    client.sendall(coded[send_data_pointer:])
                    break
                client.sendall(coded[send_data_pointer: send_data_pointer + 1024])
                send_data_size -= 1024
                send_data_pointer += 1024
            return True
        except Exception as e:
            e_str = 'Error occurred during sending process: '
            if self._error == 'strict': raise PacketError(e_str, e.args)
            else:
                e_str = '[TCPPacketErr]' + e_str
                err = PacketError(e_str, e.args)
                if self._use_logger: self._logw.error(err)
                else: print(err)
            return False

    def recvPacket(self, client: _socket, key: bytes = None,
                   serialization_method: int = SM_JSON) -> _Any:
        r'''
        通过`client`接收信息.
        参数说明:
        - `client`: TCP链接的`socket`对象
        - `key`: 解密时使用的密钥
        - `pickle`: 若为真，将接收数据反序列化，否则使用json复原对象
        '''
        try:
            size = 0
            pack_header = b''
            while size < 2:
                data = client.recv(2 - size)
                if not data: raise ConnectionError('peer closed.')
                else: 
                    pack_header += data
                    size = len(pack_header)
            
            size = 0
            pack_size = int.from_bytes(pack_header, 'big')
            pack_ = b''
            while size < pack_size:
                recv_size = pack_size - size
                if recv_size > 1024:
                    recv_size = 1024
                pack_ += client.recv(recv_size)
                size = len(pack_)
        except Exception as e:
            e_str = 'Error occurred during recv process: '
            if self._error == 'strict': raise PacketError(e_str, e.args)
            else:
                e_str = '[TCPPacketErr]' + e_str
                err = PacketError(e_str, e.args)
                if self._use_logger: self._logw.error(err)
                else: print(err)
            return None
        
        try: decoded = self._encoder.decrypt(pack_, key)
        except Exception as e:
            e_str = f'Can not decode packet with \'{self._encoder.name}\' while recving: '
            if self._error == 'strict': raise PacketError(e_str, e.args)
            else:
                e_str = '[TCPPacketErr]' + e_str
                err = PacketError(e_str, e.args)
                if self._use_logger: self._logw.error(err)
                else: print(err)
            return None
        else:
            if serialization_method == SM_JSON:
                try: obj = _loads(decoded.decode('utf-8'))
                except Exception as e:
                    if self._error == 'strict': raise PacketError('Fail JSON', e.args)
                    else:
                        err = PacketError('Fail JSON', e.args)
                        if self._use_logger: self._logw.error(err)
                        else: print(err)
                    return None
            elif serialization_method == SM_PICKLE:
                obj = _ploads(decoded, fix_imports = False)
            else:
                obj = decoded
            return obj
