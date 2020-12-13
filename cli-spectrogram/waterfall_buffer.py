from collections import deque

class WaterfallBuffer(object):
    """docstring for WaterfallBuffer"""
    def __init__(self, max_history=500):
        super(WaterfallBuffer, self).__init__()
        self._init_buffer(max_history=max_history)

    def _init_buffer(self, max_history):
        self.max_history = max_history
        self._buffer = deque(maxlen=self.max_history)

    def enlarge_buffer(self, max_history):
        self._init_buffer(max_history=max_history)

    def append(self, row):
        self._buffer.appendleft(row)

    def clear(self):
        self._buffer.clear()

    def get_last_row(self):
        return(self._buffer[0])

    def get_rows(self, row_count=None):
        if row_count == None:
            row_count = self.max_history
        return(self._buffer[:row_count])

