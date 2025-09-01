import django
if 'setup' in dir(django): django.setup()

from app.models import Person, Solution, SiteConfig, Site, Room


def generate_random_room(gender):
    rooms = {}
    capacities = {}

    site = Site.objects.get(id=SiteConfig.objects.get(id="site").num)
    blocks = site.get_site().get("blocks")

    for block in blocks:
        if block.get("gender") != gender: continue

        i = 1
        for _ in range(int(block["room_count"])):
            name = f"{block.get('name')} #{i:02d}"
            rooms[name] = []
            capacities[name] = int(block.get("room_capacity"))
            i += 1

    room_keys = list(rooms.keys())
    i = 0

    for person in Person.objects.filter(gender=gender).order_by("?"):
        rooms[room_keys[i]].append(person.id)

        i += 1
        i %= len(room_keys)

    s = Solution(
        name=f"Random {gender} rooms",
        gender=gender,
        site=site,
        explanation="Random Rooms",
        strategy="Random"
    )

    s.save()
    s.refresh_from_db()

    for room, ids in rooms.items():
        r = Room(
            internal_name=room,
            solution=s,
            capacity=capacities[room],
        )

        r.save()

        for id in ids:
            r.people.add(Person.objects.get(id=id))

        r.save()

    return s.id
