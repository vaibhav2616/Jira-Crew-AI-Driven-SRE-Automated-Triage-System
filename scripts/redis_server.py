"""Local Redis TCP service runner for environments without native Redis/Docker daemon."""

import signal
import sys
import fakeredis


def main() -> None:
    print("Starting Redis TCP server on 127.0.0.1:6379...")
    server = fakeredis.TcpFakeServer(("127.0.0.1", 6379))

    def handle_signal(sig, frame):
        print(f"Received signal {sig}, stopping Redis server...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    server.serve_forever()


if __name__ == "__main__":
    main()
