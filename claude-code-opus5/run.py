#!/usr/bin/env python3
"""Start the 4D tic-tac-toe server."""

import argparse

from fourd.server import serve

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve 4D tic-tac-toe on localhost.")
    parser.add_argument("--port", type=int, default=8421)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--verbose", action="store_true", help="log every request")
    args = parser.parse_args()
    serve(args.host, args.port, args.verbose)
