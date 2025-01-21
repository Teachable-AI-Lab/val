import json


def begin():
    with open('start.json', 'w') as f:
        json.dump({"start": True}, f)
    while True:
        val = input("Press s to stop. Press any other key to start: ")
        if val=="s":
            with open('start.json', 'w') as f:
                json.dump({"start": False}, f)
        else:
            with open('start.json', 'w') as f:
                json.dump({"start": True}, f)


if __name__=="__main__":
    begin()