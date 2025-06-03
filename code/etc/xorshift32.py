from string import ascii_letters, digits
from random import random
from typing import (
    Union,
    List,
    Tuple,
    Dict,
    Set,
    Any
)



class XorShift32:
    state: int
    MASK32: int

    def __init__(self, *, seed: float = random()):
        # Generally faster than random
        self.MASK32 = 0xFFFFFFFF
        self.seed = seed
        self.state = int(self.seed * 10000) & self.MASK32


    def next(self):
        self.state ^= (self.state << 13) & self.MASK32
        self.state ^= (self.state >> 17) & self.MASK32
        self.state ^= (self.state << 5) & self.MASK32
        return self.state & self.MASK32
    
    
    def choice(self, sequence: Union[List, Tuple, Dict, Set], *, amount: int = 1) -> Any:
        if len(sequence) == 0:
            self.next()
            return None
        
        if isinstance(sequence, (list, tuple, set)):
            sequence = list(sequence)
            if amount > 1:
                return [sequence[self.next() % len(sequence)] for _ in range(amount)]

            else:
                return sequence[self.next() % len(sequence)]
        
        elif isinstance(sequence, dict):
            keys = list(sequence.keys())
            if amount > 1:
                return [sequence[keys[self.next() % len(keys)]] for _ in range(amount)]

            else:
                return sequence[keys[self.next() % len(keys)]]
        
        self.next()
        return None
    
    
    def randint(self, *, start: int = 0, stop: int = 19952**1000) -> int:
        return start + (self.next() % (stop - start + 1))
    

    def randstr(self, lenght: int = 1, *, max_lenght: bool = False, printable: bool = True, strip_heroglyphs: bool = False, english_chars: bool = False) -> str:
        # The actual range is [0x00000, 0x110000),
        # but big range contains a lot of unsupported characters
        start = 0x00001
        stop = 0x010000
        result: str = ''

        if max_lenght:
            stop = 0x110000 - 1

        elif strip_heroglyphs:
            stop = 0x2300

        # Cba doing algorithms
        elif english_chars:
            letters = ascii_letters + digits
            while not len(result) == lenght:
                _result = self.next() % len(letters)
                _result = letters[_result]
                result += _result
            return result

        while not len(result) == lenght:
            _result = chr(self.randint(start=start, stop=stop))
            if printable:
                if not _result.isprintable():
                    continue
            result += _result
        return result