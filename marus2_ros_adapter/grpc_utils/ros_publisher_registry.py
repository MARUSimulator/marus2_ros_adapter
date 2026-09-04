import threading
from . import ros_handle as rh


class RosPublisherRegistry:
    _publishers = dict()
    _lock = threading.Lock()

    @classmethod
    def get_publisher(cls, topic_name: str, data_class, queue_size=10):
        if not topic_name.startswith("/"):
            topic_name = "/" + topic_name

        with cls._lock:
            publisher = cls._publishers.get(topic_name, None)
            if not publisher:
                publisher = rh.Publisher(data_class, topic_name, qos_profile=queue_size)
                cls._publishers[topic_name] = publisher

        pub_type = getattr(publisher, "msg_type", getattr(publisher, "data_class", None))
        if pub_type is not None and data_class is not None and pub_type != data_class:
            pub_name = getattr(pub_type, "__name__", str(pub_type))
            data_name = getattr(data_class, "__name__", str(data_class))
            rh.logerr(f"Publisher on topic '{topic_name}' has type {pub_name}, requested {data_name}")

        return publisher