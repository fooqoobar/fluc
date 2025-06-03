'''
# Secret
### What is this for?
* Basically, any type of encryption. Messages, source codes etc.
* Encrypt YOUR secrets with 3 layer protection.

#### Should Supported These Encodings:
* UTF-8
* UTF-16
* UTF-32
* Others might depend on the text you are trying to encrypt.

#### Supported Seeds:
* Any INT between 0 and 2147483647 (C INT max value).
'''

__author__ = 'SyncRaptorz'
__version__ = '1.2'
__license__ = 'MIT'
__copyright__ = 'Copyright 2025 © SyncRaptorz'

__all__ = (
    'InvalidData',
    'Decrypt',
    'Encrypt'
)

import random
import secrets
import sys
import io

from hashlib import sha512
from typing import (
    BinaryIO,
    Literal,
    Optional,
    Union,
    overload
)




class InvalidData(Exception):
    pass



class Secret:
    key: Optional[str]
    seed: Optional[int]
    encoding: str
    extra_layer: bool
    result: io.BytesIO

    @overload
    def __init__(
        self,
        *,
        key: str,
        seed: int,
        encoding: Literal['utf-8', 'utf-16', 'utf-32'] = ...,
        extra_layer: bool = ...,
        random_encrypt: Literal[False] 
    ): ...

    @overload
    def __init__(
        self,
        *,
        key: Optional[str] = None,
        seed: Optional[int] = None,
        encoding: Literal['utf-8', 'utf-16', 'utf-32'] = ...,
        extra_layer: bool = ...,
        random_encrypt: Literal[True] 
    ): ...
    
    def __init__(
        self,
        *,
        key: Optional[str] = None,
        seed: Optional[int] = None,
        encoding: Literal['utf-8', 'utf-16', 'utf-32'] = 'utf-8',
        extra_layer: bool = True,
        random_encrypt: bool = False
    ):
        self.key = key
        self.seed = seed
        self.encoding = encoding
        self.extra_layer = extra_layer
        
        if random_encrypt is True:
            if self.key is None:
                key = self.randomize_key(string=secrets.token_hex(32), count=random.randrange(8, 32))
                self.key = key
          
            if self.seed is None:
                seed = secrets.randbits(3**3)
                self.seed = seed
       
            if self.encoding is None:
                self.encoding = random.choice(['utf-8', 'utf-16', 'utf-32'])
            
        if None in (key, seed):
            self.extra_layer = False
            
        else:
            # Sometimes the seed is too big
            if seed:
                if seed > 2147483647:
                    raise ValueError('INTs larger than 2147483647 not supported at this moment')

                if seed >= 640:
                    sys.set_int_max_str_digits(seed)


    def randomize_key(self, string: str, count: int):
        indices = random.sample(range(len(string)), min(count, len(string)))
        return ''.join(c.upper() if i in indices else c for i, c in enumerate(string))


    def _obfuscate(self, content: str) -> str:
        result = []
        i = 0

        while i < len(content):
            length = random.randint(100, 200)
            result.append(content[i:i+length])
            i += length
        return str('\n'.join(result))
    

    # Extra layer of encryption using key and seed
    def _generate_key(self) -> list:
        random.seed(self.seed)
        salt = ''.join(chr(random.randint(0x2500, 0x2BFF)) for _ in range(16))
        combined_key = f"{self.key}{self.seed}{salt}".encode(encoding=self.encoding)
        hashed_key = sha512(combined_key).digest()
        return [b for b in hashed_key]


    def _scramble(self, data: str, key_bytes: list) -> str:
        scrambled = [chr((ord(c) + key_bytes[i % len(key_bytes)]) % 0x10FFFF) for i, c in enumerate(data)]
        return ''.join(scrambled)


    def _unscramble(self, data: str, key_bytes: list) -> str:
        unscrambled = [chr((ord(c) - key_bytes[i % len(key_bytes)]) % 0x10FFFF) for i, c in enumerate(data)]
        return ''.join(unscrambled)


    def _encrypt2(self, text: str) -> str:
        key_bytes = self._generate_key()
        scrambled = self._scramble(text, key_bytes)
        encrypted_bytes = [(ord(c) ^ key_bytes[i % len(key_bytes)]) % 0x10FFFF for i, c in enumerate(scrambled)]
        return ''.join(chr(b) for b in encrypted_bytes)


    def _decrypt2(self, cipher: str) -> str:
        key_bytes = self._generate_key()
        decrypted_bytes = [(ord(c) ^ key_bytes[i % len(key_bytes)]) % 0x10FFFF for i, c in enumerate(cipher)]
        decrypted_str = ''.join(chr(b) for b in decrypted_bytes)
        return self._unscramble(decrypted_str, key_bytes)



class Encrypt(Secret):
    def _length_encode(self, binary: str) -> str:
        encoded = ''
        count = 1

        for i in range(1, len(binary)):
            if binary[i] == binary[i-1]:
                count += 1
           
            else:
                encoded += str(count) + binary[i-1]
                count = 1
                
        encoded += str(count) + binary[-1]
        return encoded


    def _reverse_bits(self, binary: str) -> str:
        return ''.join('1' if b == '0' else '0' for b in binary)[::-1]


    def _encrypt(self, content: Union[str, bytes]) -> io.BytesIO:
        buffer = io.BytesIO()
        
        if isinstance(content, str):
            content = content.encode(encoding=self.encoding)
        
        decoded_data = ''.join(format(byte, '08b') for byte in content)
        
        for i in range(0, len(decoded_data), 8):
            binary = decoded_data[i:i+8]
            reversed_binary = self._reverse_bits(binary)
            encoded = self._length_encode(reversed_binary)
            buffer.write(encoded.encode(encoding=self.encoding))

        buffer.seek(0)
        result = io.BytesIO()
        
        if self.extra_layer is True:
            string = self._encrypt2(buffer.read().decode(encoding=self.encoding))
            
        else:
            string = buffer.read().decode(encoding=self.encoding)
        # For appearance xD
        string = self._obfuscate(string)
        
        result.write(string.encode(encoding=self.encoding))
        result.seek(0)
        
        self.result = result
        return result


    def from_file(self, file: BinaryIO) -> io.BytesIO:
        return self._encrypt(file.read())


    def from_bytes(self, content: bytes) -> io.BytesIO:
        try:
            decoded: str = content.decode(self.encoding)
        
        except ValueError:
            raise InvalidData
        return self._encrypt(decoded)


    def from_str(self, content: str) -> io.BytesIO:
        return self._encrypt(content)
    
    

class Decrypt(Secret):
    def _length_decode(self, encoded: Union[str, bytes]) -> str:
        decoded = ''
        i = 0

        while i < len(encoded):
            if self.encoding in ('utf-32', 'utf-16'):
                # Skip BOM because it causes errors (and it's not neccessary in most cases)
                if not encoded[i] or encoded[i] == '\ufeff':
                    i += 1
                    continue
            
            count = int(encoded[i])
            i += 1
            decoded += str(encoded[i]) * count
            i += 1
        return decoded
    

    def _reverse_bits(self, binary: str) -> str:
        return ''.join('0' if b == '1' else '1' for b in binary)[::-1]


    def _decrypt(self, content: bytes) -> io.BytesIO:
        # Replace the \n with ''
        try:
            content = content.decode(encoding=self.encoding).replace('\n', '').encode(encoding=self.encoding)

            if self.extra_layer is True:
                content = self._decrypt2(content.decode(self.encoding)).encode(self.encoding)
            decoded = self._length_decode(content.decode(self.encoding))

        except (ValueError, UnicodeDecodeError):
            raise InvalidData(f'The given data is not valid') from None

        buffer = io.BytesIO()
        
        for i in range(0, len(decoded), 8):
            binary = decoded[i:i+8]
            reversed_binary = self._reverse_bits(binary)
            reversed_binary = int(reversed_binary, 2).to_bytes(1, 'big')
            buffer.write(reversed_binary)
        
        buffer.seek(0)
        self.result = buffer
        return buffer
        

    def from_file(self, file: BinaryIO) -> io.BytesIO:
        return self._decrypt(file.read())
    

    def from_bytes(self, binary: bytes) -> io.BytesIO:
        return self._decrypt(binary)
    

    def from_str(self, binary: str) -> io.BytesIO:
        try:
            payload = binary.encode(self.encoding)
        
        except ValueError:
            raise InvalidData
        return self._decrypt(payload)