import argparse
import json
import socket
import threading

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


def send_json(sock, message, send_lock):
    encoded = (json.dumps(message) + "\n").encode("utf-8")

    try:
        with send_lock:
            sock.sendall(encoded)
        return True
    except OSError as error:
        print(f"Send failed: {error}")
        return False


def receive_responses(sock, stop_event):
    buffer = b""

    try:
        while not stop_event.is_set():
            data = sock.recv(4096)

            if not data:
                if not stop_event.is_set():
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

                print(f"\nBroker response: {message}")

    except OSError as error:
        if not stop_event.is_set():
            print(f"\nReceive failed: {error}")

    finally:
        stop_event.set()


def main():
    parser = argparse.ArgumentParser(description="Publish-subscribe publisher")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
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
    print("Enter a topic and message separated by |")
    print("Example: sports | Goal!")
    print("Enter quit to disconnect.")

    receiver = threading.Thread(
        target=receive_responses,
        args=(sock, stop_event),
        daemon=True
    )
    receiver.start()

    try:
        while not stop_event.is_set():
            try:
                user_input = input("publisher> ").strip()
            except EOFError:
                break

            if user_input.lower() == "quit":
                break

            if "|" not in user_input:
                print("Invalid format. Use: topic | message")
                continue

            topic, content = user_input.split("|", 1)
            topic = topic.strip()
            content = content.strip()

            if not topic or not content:
                print("Both topic and message must be non-empty.")
                continue

            success = send_json(
                sock,
                {
                    "type": "PUBLISH",
                    "topic": topic,
                    "message": content
                },
                send_lock
            )

            if not success:
                break

    except KeyboardInterrupt:
        print("\nDisconnecting...")

    finally:
        stop_event.set()

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        sock.close()
        print("Publisher disconnected.")


if __name__ == "__main__":
    main()
