# Publish–Subscribe Messaging System with SDN

## 1. Project Overview

This project implements a publish–subscribe messaging application consisting
of publishers, a broker, and subscribers.

TCP sockets provide reliable communication between application components.
The broker manages topic subscriptions and forwards published messages to
subscribers interested in the corresponding topics.

Software-Defined Networking (SDN) provides centralized network control
through an SDN controller communicating with network switches using
OpenFlow.

## 2. Architecture

Publisher → TCP → Broker → TCP → Subscribers

The publisher sends messages to the broker.
The broker matches each published message against active topic subscriptions.
Subscribers receive messages for the topics to which they are subscribed.

The broker handles application-level topic matching. The SDN controller
manages network forwarding.

## 3. Network Topology

The planned Mininet topology contains four switches and four hosts.

| Host | Role | IP address |
|------|------|------------|
| h1 | Publisher | 10.0.0.1 |
| h2 | Broker | 10.0.0.2 |
| h3 | Subscriber 1 | 10.0.0.3 |
| h4 | Subscriber 2 | 10.0.0.4 |

The broker listens on TCP port 5000.

The planned network has two paths between s1 and s4:

- Path A: s1 → s2 → s4
- Path B: s1 → s3 → s4

## 4. Application Protocol

The application uses JSON messages delimited by newline characters.
Each JSON message must end with a newline (`\n`).

### Publish a message

{"type":"PUBLISH","topic":"sports","message":"Goal!"}

### Subscribe to a topic

{"type":"SUBSCRIBE","topic":"sports"}

### Unsubscribe from a topic

{"type":"UNSUBSCRIBE","topic":"sports"}

### Message delivered by the broker

{"type":"MESSAGE","topic":"sports","message":"Goal!"}

The broker also sends status responses such as SUBSCRIBED,
UNSUBSCRIBED, and ERROR.

## 5. Prerequisites

- Python 3
- Git
- The project's Python virtual environment for local development
- Mininet and Open vSwitch for network integration
- An agreed SDN controller supporting the required OpenFlow version

## 6. Local Application Testing

From the project root, activate the virtual environment:

    source .venv/bin/activate

Start the broker in one terminal:

    python3 broker/broker.py

Start a subscriber in another terminal:

    python3 subscriber/subscriber.py

At the subscriber prompt, enter:

    sub sports

Start the publisher in another terminal:

    python3 publisher/publisher.py

Enter the following at the publisher prompt:

    sports | Goal!

The subscribed client should receive the published message.

To unsubscribe, enter the following at the subscriber prompt:

    unsub sports

To exit, enter:

    quit

## 7. Mininet Integration

The planned deployment assigns the publisher to h1, the broker to h2,
Subscriber 1 to h3, and Subscriber 2 to h4.

The broker listens on 0.0.0.0:5000 so that it can accept connections
through its network interfaces.

The publisher and subscriber clients support specifying the broker's
host address and port.

Example client command:

    python3 publisher/publisher.py --host 10.0.0.2 --port 5000

The Mininet topology, host connectivity, and SDN controller must be
configured and verified before these network integration tests are run.

## 8. Repository Structure

    broker/
        broker.py
    publisher/
        publisher.py
    subscriber/
        subscriber.py
    sdn/
        controller.py
    topology/
        topology.py
    tests/
    results/
    docs/

## 9. Team Responsibilities

- Member 1: Publisher, subscriber, broker, TCP communication protocol,
  application testing, and application integration.
- Member 2: Mininet topology, host addressing, and network connectivity.
- Member 3: SDN controller, OpenFlow support, and switch-controller
  integration.


