__author__ = "Frederik Lauber"
__copyright__ = "Copyright 2014"
__license__ = "GPL3"
__version__ = "0.5"
__maintainer__ = "Frederik Lauber"
__status__ = "Production"
__contact__ = "https://flambda.de/impressum.html"

import threading
from collections import deque


class SelfFlushingQueue:
    def __init__(self, maxsize=10):
        self.maxsize = maxsize
        self.deque = deque()
        self.mutex = threading.Lock()
        self.has_item = threading.Condition(self.mutex)

    def put(self, item):
        with self.mutex:
            if len(self.deque) >= self.maxsize:
                self.deque = deque()
            self.deque.append(item)
            self.has_item.notify()

    def get(self):
        with self.has_item:
            if not len(self.deque):
                self.has_item.wait()
            item = self.deque.popleft()
            return item


class propergate_and_flush(threading.Thread):
    def __init__(self, input_queue, output_queue_set, set_lock):
        super().__init__()
        self._stop = threading.Event()
        self.daemon = True
        self.input_queue = input_queue
        self.output_queue_set = output_queue_set
        self.set_lock = set_lock

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        while not self._stop.isSet():
            value = self.input_queue.get()
            with self.set_lock:
                for q in self.output_queue_set:
                    q.put(value)



class QueueManager(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, queue_size=16):
        if queue_size <= 0:
            raise ValueError
        self._lock = threading.Lock()
        self.input_queues = {}
        self.output_queue_sets = {}
        self.output_queue_locks = {}
        self.queue_threads = {}
        self.queue_size = queue_size

    def reg_output_queue(self, identifier):
        with self._lock:
            tmp = SelfFlushingQueue(maxsize=self.queue_size)
            tmp_lock = threading.Lock()
            if not identifier in self.input_queues:
                raise Exception
            if identifier in self.output_queue_sets:
                with self.output_queue_locks[identifier]:
                    self.output_queue_sets[identifier].add(tmp)
            else:
                self.output_queue_sets[identifier] = set([tmp])
                tmp_lock = threading.Lock()
                self.output_queue_locks[identifier] = tmp_lock
                self.queue_threads[identifier] = propergate_and_flush(self.input_queues[identifier], self.output_queue_sets[identifier], tmp_lock)
                self.queue_threads[identifier].start()
            return tmp

    def reg_input_queue(self, identifier, queueclass=SelfFlushingQueue, queue_size=None):
        queue_size = queue_size or self.queue_size
        with self._lock:
            if identifier in self.input_queues:
                raise Exception
            tmp = queueclass(maxsize=queue_size)
            self.input_queues[identifier] = tmp
            return tmp

    def del_input_queue(self, identifier):
        with self._lock:
            if identifier in self.input_queues:
                self.queue_threads[identifier].stop()
                self.queue_threads.pop(identifier, None)
                self.input_queues.pop(identifier, None)
                self.output_queue_sets.pop(identifier, None)
            else:
                raise Exception

    def del_output_queue(self, identifier, queue):
        with self._lock:
            if identifier in self.output_queue_sets:
                self.output_queue_sets[identifier].discard(queue)
                if len(self.output_queue_sets[identifier]) == 0:
                    self.queue_threads[identifier].stop()
                    self.queue_threads.pop(identifier, None)
                    self.output_queue_sets.pop(identifier, None)
                    self.output_queue_locks.pop(identifier, None)
            else:
                raise Exception