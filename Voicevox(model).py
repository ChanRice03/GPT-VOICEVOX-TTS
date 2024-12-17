import requests
from rich import print

host = "127.0.0.1"
port = "50021"


def get_speakers():
    res = requests.get(f"http://{host}:{port}/speakers")
    print(res.json())


if __name__ == "__main__":
    get_speakers()