# Roomies
A sorta-smart roommate matching tool for overnight field trips that will hopefully make my job as a member of the trip committee easier.

## Technologies Used
* Python / Django
* HTML / Bootstrap
* JS (a _very_ small amount)

## Here to Grade This?
You can find a test environment running this code at `REDACTED`. A few notes:
* Data is real sample data I collected from my students, but has been anonymized (students will show up as, for example, "Person 1" instead of "John Smith".)
* Test Student: `REDACTED`
* Test Admin: `REDACTED`

If you haven't had experience with Django before, there's a lot more boilerplate than Flask. The vast majority of my code can be found in `app/views` and `app/templates`

### Instructions for Use
1. Admin logs in with admin account (see credentials above)
2. Admin uploads CSV with student names, IDs, and genders (already done in test environment)
3. Admin opens site for student logins (already done in test environment)
4. Students log in by selecting their name and entering their student ID from the homepage (you may use test student above)
5. Students input up to 3 requests
6. Admin closes site for student logins via admin panel
7. Admin starts room generation script (located at `app/utils/sum.py`), currently must be started via command line
8. Admin can view, tweak, and print room list for male and female students via admin panel

## Matching Algorithm
Current best algorithm... A bit "brute force-y" but that's okay for this use case.
1. "Seed" the needed number of rooms with one random student each
2. Until students are all placed, loop through rooms round-robin style (ie, Room 1, Room 2, Room 3, Room 1, Room 2, etc) and:
    1. Sort all unplaced students by their "attraction" to students currently in that room. That is, the number of requests going from the unplaced student to member of the room, plus the number of requests from members of the room to the unplaced student
    2. Place the student with the highest "attraction" into the room
3. Give the solution a "penalty score" by the number of unmet requests, further penalizing the solution by number of students with multiple unmet requests
4. Repeat many times (in testing, 1000 iterations was sufficient, took ~5 mins per gender)
5. Save the solution(s) that have the lowest score to the database.