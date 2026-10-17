import argparse
import json
import socket
import threading

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
BUFFER_SIZE = 4096


def send_json(sock, message, send_lock):
    encoded = (json.dumps(message) + "\n").encode("utf-8")

    try:
        with send_lock:
            sock.sendall(encoded)
        return True
    except OSError as error:
        print(f"Send failed: {error}")
        return False


def receive_messages(sock, stop_event):
    buffer = b""

    try:
        while not stop_event.is_set():
            data = sock.recv(BUFFER_SIZE)

            if not data:
                print("\nBroker disconnected.")
                break

            buffer += data

            while b"\n" in buffer:
                raw_message, buffer = buffer.split(b"\n", 1)

                if not raw_message.strip():
                    continue

                try:
                    message = json.loads(raw_message.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    print("\nReceived invalid JSON from broker.")
                    continue

                message_type = message.get("type")

                if message_type == "MESSAGE":
                    print(
                        f"\n[NEW MESSAGE] Topic: {message.get('topic')} | "
                        f"Message: {message.get('message')}"
                    )
                elif message_type == "SUBSCRIBED":
                    print(f"\nSubscribed to topic: {message.get('topic')}")
                elif message_type == "UNSUBSCRIBED":
                    print(f"\nUnsubscribed from topic: {message.get('topic')}")
                elif message_type == "ERROR":
                    print(f"\nBroker error: {message.get('message')}")
                else:
                    print(f"\nBroker response: {message}")

    except OSError as error:
        if not stop_event.is_set():
            print(f"\nReceive failed: {error}")

    finally:
        stop_event.set()


def main():
    parser = argparse.ArgumentParser(description="Publish-subscribe client")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    stop_event = threading.Event()
    send_lock = threading.Lock()

    try:
        sock = socket.create_connection((args.host, args.port), timeout=5)
        sock.settimeout(None)
    except OSError as error:
        print(f"Could not connect to broker at {args.host}:{args.port}: {error}")
        return

    print(f"Connected to broker at {args.host}:{args.port}")
    print("Commands:")
    print("  sub <topic>     Subscribe to a topic")
    print("  unsub <topic>   Unsubscribe from a topic")
    print("  quit            Disconnect and exit")

    receiver = threading.Thread(
        target=receive_messages,
        args=(sock, stop_event),
        daemon=True
    )
    receiver.start()

    try:
        while not stop_event.is_set():
            try:
                command = input("subscriber> ").strip()
            except EOFError:
                break

            if not command:
                continue

            parts = command.split(maxsplit=1)
            action = parts[0].lower()

            if action == "quit":
                break

            if action in ("sub", "unsub"):
                if len(parts) != 2 or not parts[1].strip():
                    print("Usage: sub <topic> or unsub <topic>")
                    continue

                topic = parts[1].strip()

                message_type = (
                    "SUBSCRIBE" if action == "sub" else "UNSUBSCRIBE"
                )

                success = send_json(
                    sock,
                    {"type": message_type, "topic": topic},
                    send_lock
                )

                if not success:
                    break
            else:
                print("Unknown command. Use sub, unsub, or quit.")

    except KeyboardInterrupt:
        print("\nDisconnecting...")

    finally:
        stop_event.set()

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        sock.close()
        print("Subscriber disconnected.")


if __name__ == "__main__":
    main()
