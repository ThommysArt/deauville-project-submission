import json


def main():
    with open("data/festival.json") as f:
        data = json.load(f)
        print(data["name"])
        print("From " + data["first_day"] + " to " + data["last_day"])
        print(
            str(len(data["venues"]))
            + " venues, "
            + str(len(data["artists"]))
            + " artists, "
            + str(len(data["performances"]))
            + " performances"
        )


if __name__ == "__main__":
    main()
