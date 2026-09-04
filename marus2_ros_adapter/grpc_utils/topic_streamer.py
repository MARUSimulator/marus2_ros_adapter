import threading
import time
from queue import Queue, Empty, Full
from . import ros_handle as rh


class Streamer:
    """
    Server streaming service helper with thread-safe client buffers
    and robust overflow management.
    """

    def __init__(self, make_response, topic_msg_type, callbacks=None):
        self._lock = threading.Lock()
        self._registered_clients = {}
        self._address_to_clients_map = {}
        self._subscriptions = {}
        self._thread_sleep_if_empty = 0.01
        self._callbacks = callbacks or {}
        self._topic_msg_type = topic_msg_type
        self._make_response = make_response

    def _normalize_address(self, address: str) -> str:
        addr = address.strip().lower()
        if not addr.startswith("/"):
            addr = "/" + addr
        return addr

    def _subscribe_to_topic(self, address: str, msg_type):
        def callback(msg, *args):
            with self._lock:
                clients = list(self._address_to_clients_map.get(address, []))
                buffers = [self._registered_clients.get((cl, address)) for cl in clients]

            for buf in buffers:
                if buf is not None:
                    try:
                        buf.put_nowait(msg)
                    except Full:
                        try:
                            buf.get_nowait()
                            buf.put_nowait(msg)
                        except (Empty, Full):
                            pass

        sub = rh.Subscription(msg_type, address, callback, qos_profile=10)
        self._subscriptions[address] = sub

    def start_stream(self, request, context):
        client_id = context.peer()
        address = self._normalize_address(request.address)
        request_buffer = Queue(maxsize=100)

        with self._lock:
            self._registered_clients[(client_id, address)] = request_buffer

            if address not in self._address_to_clients_map:
                self._address_to_clients_map[address] = []
                self._subscribe_to_topic(address, self._topic_msg_type)

            if client_id not in self._address_to_clients_map[address]:
                self._address_to_clients_map[address].append(client_id)

        try:
            while True:
                if not context.is_active():
                    break

                try:
                    data = request_buffer.get(timeout=0.1)
                except Empty:
                    continue

                try:
                    response = self._make_response(data)
                except Exception as e:
                    rh.logerr(f"Cannot create response message for topic {address}: {repr(e)}")
                    continue

                yield response
        finally:
            self._remove_client(address, client_id)

    def _remove_client(self, address: str, client_id: str):
        with self._lock:
            self._registered_clients.pop((client_id, address), None)
            cl_list = self._address_to_clients_map.get(address, [])
            if client_id in cl_list:
                cl_list.remove(client_id)
            if not cl_list and address in self._address_to_clients_map:
                del self._address_to_clients_map[address]
                # If subscription object has destroy(), destroy it
                sub = self._subscriptions.pop(address, None)
                if sub is not None and hasattr(sub, "destroy"):
                    try:
                        sub.destroy()
                    except Exception:
                        pass
