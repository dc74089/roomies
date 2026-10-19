from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from app.models import Person, Request, Room, Solution
from app.utils.evaluate import evaluate_solution


class SolutionEditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("admin", password="pw", is_staff=True)
        self.client.force_login(self.user)

        self.a, self.b, self.c, self.d = [
            Person.objects.create(id=str(100 + i), name=f"Student {i}", gender="female") for i in range(4)
        ]
        self.other_gender = Person.objects.create(id="200", name="Someone Else", gender="male")
        self.unplaced = Person.objects.create(id="104", name="Student 4", gender="female")

        Request.objects.create(requestor=self.a, requestee=self.b, type="attract")
        Request.objects.create(requestor=self.c, requestee=self.a, type="attract")
        Request.objects.create(requestor=self.a, requestee=self.d, type="forbid", manual=True)

        self.solution = Solution.objects.create(name="Test", gender="female", explanation="")
        self.room1 = Room.objects.create(internal_name="Room #01", solution=self.solution, capacity=2, placed_name="")
        self.room2 = Room.objects.create(internal_name="Room #02", solution=self.solution, capacity=3, placed_name="")
        self.room1.people.add(self.a, self.c)
        self.room2.people.add(self.b, self.d)

    def room_of(self, person):
        return self.solution.rooms.filter(people=person).first()

    # ---- Page -------------------------------------------------------------

    def test_page_payload(self):
        res = self.client.get(reverse("admin_edit_solution", args=[self.solution.id]))
        self.assertEqual(res.status_code, 200)

        payload = res.context["payload"]
        self.assertEqual([r["internal_name"] for r in payload["rooms"]], ["Room #01", "Room #02"])
        self.assertEqual(sorted(payload["rooms"][0]["people"]), ["100", "102"])
        self.assertEqual(payload["unplaced"], ["104"])
        self.assertNotIn("200", [p["id"] for p in payload["people"]])
        self.assertEqual(len(payload["requests"]), 3)
        self.assertContains(res, 'id="solution-data"')

    def test_page_missing_solution_404s(self):
        res = self.client.get(reverse("admin_edit_solution", args=[9999]))
        self.assertEqual(res.status_code, 404)

    # ---- Move ---------------------------------------------------------------

    def test_move_to_room(self):
        res = self.client.post(reverse("admin_move_student"), {
            "solution": self.solution.id, "person": self.a.id, "to": self.room2.id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.room_of(self.a), self.room2)
        self.assertNotIn(self.a, self.room1.people.all())

    def test_move_to_unplaced(self):
        res = self.client.post(reverse("admin_move_student"), {
            "solution": self.solution.id, "person": self.a.id, "to": ""})
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(self.room_of(self.a))

    def test_move_from_unplaced(self):
        self.client.post(reverse("admin_move_student"), {
            "solution": self.solution.id, "person": self.unplaced.id, "to": self.room2.id})
        self.assertEqual(self.room_of(self.unplaced), self.room2)

    def test_move_to_room_in_other_solution_404s(self):
        other = Solution.objects.create(name="Other", gender="female", explanation="")
        foreign = Room.objects.create(internal_name="X", solution=other, capacity=2)
        res = self.client.post(reverse("admin_move_student"), {
            "solution": self.solution.id, "person": self.a.id, "to": foreign.id})
        self.assertEqual(res.status_code, 404)
        # Rolled back: still in the original room
        self.assertEqual(self.room_of(self.a), self.room1)

    def test_move_requires_post_and_fields(self):
        self.assertEqual(self.client.get(reverse("admin_move_student")).status_code, 400)
        self.assertEqual(self.client.post(reverse("admin_move_student"), {"solution": self.solution.id}).status_code, 400)

    # ---- Swap ---------------------------------------------------------------

    def test_swap(self):
        res = self.client.post(reverse("admin_swap_students"), {
            "solution": self.solution.id, "a": self.a.id, "b": self.b.id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.room_of(self.a), self.room2)
        self.assertEqual(self.room_of(self.b), self.room1)

    def test_swap_same_room_rejected(self):
        res = self.client.post(reverse("admin_swap_students"), {
            "solution": self.solution.id, "a": self.a.id, "b": self.c.id})
        self.assertEqual(res.status_code, 400)

    def test_swap_with_unplaced_rejected(self):
        res = self.client.post(reverse("admin_swap_students"), {
            "solution": self.solution.id, "a": self.a.id, "b": self.unplaced.id})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.room_of(self.a), self.room1)

    # ---- Rename -------------------------------------------------------------

    def test_rename(self):
        res = self.client.post(reverse("admin_rename_room"), {"id": self.room1.id, "new": "  214 "})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["placed_name"], "214")
        self.room1.refresh_from_db()
        self.assertEqual(self.room1.placed_name, "214")

    def test_rename_clear(self):
        self.client.post(reverse("admin_rename_room"), {"id": self.room1.id, "new": ""})
        self.room1.refresh_from_db()
        self.assertEqual(self.room1.placed_name, "")

    # ---- Re-evaluate --------------------------------------------------------

    def test_reevaluate_updates_score(self):
        res = self.client.get(reverse("admin_reevaluate_solution"), {"solution": self.solution.id})
        self.assertEqual(res.status_code, 200)
        self.solution.refresh_from_db()
        self.assertEqual(res.json()["score"], self.solution.score)
        self.assertEqual(self.solution.score, evaluate_solution(self.solution)[0])

    # ---- Security -----------------------------------------------------------

    def test_endpoints_require_login(self):
        anon = Client()
        checks = [
            ("get", reverse("admin_edit_solution", args=[self.solution.id]), {}),
            ("post", reverse("admin_move_student"), {"solution": self.solution.id, "person": self.a.id, "to": ""}),
            ("post", reverse("admin_swap_students"), {"solution": self.solution.id, "a": self.a.id, "b": self.b.id}),
            ("post", reverse("admin_rename_room"), {"id": self.room1.id, "new": "x"}),
            ("get", reverse("admin_reevaluate_solution"), {"solution": self.solution.id}),
        ]
        for method, url, data in checks:
            res = getattr(anon, method)(url, data)
            self.assertEqual(res.status_code, 302, url)
            self.assertTrue(res.url.startswith("/login"), url)

        self.assertEqual(self.room_of(self.a), self.room1)

    def test_move_requires_csrf(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        res = strict.post(reverse("admin_move_student"), {
            "solution": self.solution.id, "person": self.a.id, "to": ""})
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.room_of(self.a), self.room1)
