import json
import socket
import threading

HOST = "0.0.0.0"
PORT = 5000
BUFFER_SIZE = 4096

subscriptions = {}
clients = set()
clients_lock = threading.Lock()
send_locks = {}


def send_json(client_socket, message):
    encoded = (
        json.dumps(message, separators=(",", ":")) + "\n"
    ).encode("utf-8")

    with clients_lock:
        lock = send_locks.get(client_socket)

    if lock is None:
        return False

    try:
        with lock:
            client_socket.sendall(encoded)
        return True
    except (OSError, ConnectionError):
        return False


def remove_client(client_socket):
    with clients_lock:
        clients.discard(client_socket)
        send_locks.pop(client_socket, None)

        for topic in list(subscriptions):
            subscriptions[topic].discard(client_socket)

            if not subscriptions[topic]:
                del subscriptions[topic]


def handle_message(client_socket, message):
    message_type = message.get("type")

    if message_type == "SUBSCRIBE":
        topic = message.get("topic")

        if not isinstance(topic, str) or not topic.strip():
            send_json(client_socket, {
                "type": "ERROR",
                "message": "A non-empty topic is required."
            })
            return

        topic = topic.strip()

        with clients_lock:
            if client_socket not in clients:
                return

            subscriptions.setdefault(topic, set()).add(client_socket)

        send_json(client_socket, {
            "type": "SUBSCRIBED",
            "topic": topic
        })

        print(f"Client subscribed to topic: {topic}")

    elif message_type == "UNSUBSCRIBE":
        topic = message.get("topic")

        if not isinstance(topic, str) or not topic.strip():
            send_json(client_socket, {
                "type": "ERROR",
                "message": "A non-empty topic is required."
            })
            return

        topic = topic.strip()

        with clients_lock:
            subscribers = subscriptions.get(topic)

            if subscribers is not None:
                subscribers.discard(client_socket)

                if not subscribers:
                    del subscriptions[topic]

        send_json(client_socket, {
            "type": "UNSUBSCRIBED",
            "topic": topic
        })

        print(f"Client unsubscribed from topic: {topic}")

    elif message_type == "PUBLISH":
        topic = message.get("topic")
        content = message.get("message")

        if (
            not isinstance(topic, str)
            or not topic.strip()
            or not isinstance(content, str)
        ):
            send_json(client_socket, {
                "type": "ERROR",
                "message": "PUBLISH requires a topic and string message."
            })
            return

        topic = topic.strip()

        delivery = {
            "type": "MESSAGE",
            "topic": topic,
            "message": content
        }

        with clients_lock:
            recipients = list(subscriptions.get(topic, set()))

        delivered = 0

        for recipient in recipients:
            if send_json(recipient, delivery):
                delivered += 1
            else:
                remove_client(recipient)

        print(
            f"Published to topic '{topic}': "
            f"{content!r} | delivered to {delivered} subscriber(s)"
        )

    else:
        send_json(client_socket, {
            "type": "ERROR",
            "message": "Unsupported message type."
        })


def client_worker(client_socket, client_address):
    print(f"Client connected: {client_address}")

    buffer = b""

    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE)

            if not data:
                break

            buffer += data

            while b"\n" in buffer:
                raw_message, buffer = buffer.split(b"\n", 1)

                if not raw_message.strip():
                    continue

                try:
                    message = json.loads(raw_message.decode("utf-8"))

                    if not isinstance(message, dict):
                        raise ValueError("JSON message must be an object")

                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    send_json(client_socket, {
                        "type": "ERROR",
                        "message": "Invalid JSON message."
                    })
                    continue

                handle_message(client_socket, message)

    except (OSError, ConnectionError) as error:
        print(f"Connection error for {client_address}: {error}")

    finally:
        remove_client(client_socket)

        try:
            client_socket.close()
        except OSError:
            pass

        print(f"Client disconnected: {client_address}")


def start_broker():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        print(f"Broker listening on {HOST}:{PORT}")

        while True:
            client_socket, client_address = server_socket.accept()

            with clients_lock:
                clients.add(client_socket)
                send_locks[client_socket] = threading.Lock()

            worker = threading.Thread(
                target=client_worker,
                args=(client_socket, client_address),
                daemon=True
            )
            worker.start()

    except KeyboardInterrupt:
        print("\nBroker shutting down.")

    finally:
        server_socket.close()

        with clients_lock:
            active_clients = list(clients)

        for client_socket in active_clients:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                client_socket.close()
            except OSError:
                pass


if __name__ == "__main__":
    start_broker()
