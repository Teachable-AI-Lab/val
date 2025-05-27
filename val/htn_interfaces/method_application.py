import hashlib
from base64 import b64encode
import numpy as np


class MethodApplication:
    def __init__(self, method, match, state):
        self.method = method
        self.match = tuple(match)
        self.state = state
        self.id = self._unique_hash(self)


    def _update_unique_hash(self, m, obj):
        """
        Recursive depth-first-traversal to buildup hash
        :param m:
        :param obj:
        :return:
        """
        if isinstance(obj, str):
            m.update(obj.encode('utf-8'))
        elif isinstance(obj, (tuple, list, np.ndarray)):
            for i, x in enumerate(obj):
                self._update_unique_hash(m, i)
                self._update_unique_hash(m, x)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self._update_unique_hash(m, k)
                self._update_unique_hash(m, v)
        elif isinstance(obj, bytes):
            m.update(obj)
        else:
            m.update(str(obj).encode('utf-8'))

    def _unique_hash(self, stuff, hash_func='sha256'):
        """
        Returns a 64-bit encoded hashstring of hierarchies of basic python data
        :param stuff:
        :param hash_func:
        :return:
        """
        m = hashlib.new(hash_func)
        self._update_unique_hash(m, stuff)

        # Encode in base64 map the usual altchars '/' and "+' to 'A' and 'B".
        s = b64encode(m.digest(), altchars=b'AB').decode('utf-8')
        # Strip the trailing '='.
        s = s[:-1]
        return s

    def __hash__(self):
        return hash((
            str(self.method),
            str(self.state),
            hash(self.match)
        ))

    def __eq__(self, other):
        return (
            str(self.method) == str(other.method) and
            str(self.state) == str(other.state) and
            self.match == other.match
        )