/*
 * Dummy data for the solution-edit mockups.
 *
 * Shapes intentionally mirror the Django models so the mockups translate
 * directly into templates/JSON endpoints later:
 *   Person   {id, name, gender}
 *   Request  {requestor, requestee, type, manual}
 *   Room     {id, internal_name, placed_name, capacity, people: [personId]}
 *   Solution {id, name, strategy, gender, rooms}
 *
 * Everything is generated from a seeded PRNG so every reload is identical.
 */
(function () {
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  const rand = mulberry32(20261006);
  const pick = arr => arr[Math.floor(rand() * arr.length)];

  const FIRST = [
    "Ava", "Maya", "Sofia", "Priya", "Lena", "Zoe", "Hana", "Chloe", "Nora", "Isla",
    "Amara", "Ruby", "Leila", "Grace", "Elena", "Mia", "Tessa", "Jade", "Aria", "Lucia",
    "Naomi", "Ivy", "Clara", "Freya", "Mei", "Sana", "Willa", "Esme", "Dani", "Kira",
    "Rosa", "Talia", "Yara", "June", "Nia", "Pia", "Vera", "Iris", "Lila", "Opal",
    "Quinn", "Sage"
  ];
  const LAST = "ABCDEFGHJKLMNPRSTVWY".split("");

  // ---- People -------------------------------------------------------------
  const people = FIRST.map((first, i) => ({
    id: String(10400 + i * 7),
    name: `${first} ${pick(LAST)}.`,
    gender: "female",
  }));

  // ---- Friend clusters -> requests ---------------------------------------
  // Real request graphs are clumpy: tight friend groups with a few bridges.
  const clusterSizes = [4, 4, 5, 3, 4, 6, 4, 4, 3, 5];
  const clusters = [];
  let cursor = 0;
  for (const size of clusterSizes) {
    clusters.push(people.slice(cursor, cursor + size).map(p => p.id));
    cursor += size;
  }

  const requests = [];
  const has = (a, b) => requests.some(r => r.requestor === a && r.requestee === b);

  clusters.forEach((members, ci) => {
    members.forEach(id => {
      const want = 2 + Math.floor(rand() * 2); // 2-3 requests each
      let guard = 0;
      while (requests.filter(r => r.requestor === id && !r.manual).length < want && guard++ < 40) {
        // 80% in-cluster, 20% bridge to a neighbouring cluster
        const pool = rand() < 0.87 ? members : clusters[(ci + 1) % clusters.length];
        const target = pick(pool);
        if (target !== id && !has(id, target)) {
          requests.push({requestor: id, requestee: target, type: "attract", manual: false});
        }
      }
    });
  });

  // A couple of student-submitted "not with" requests
  requests.push({requestor: people[3].id, requestee: people[30].id, type: "repel", manual: false});
  requests.push({requestor: people[17].id, requestee: people[12].id, type: "repel", manual: false});

  // Admin-entered hard constraints (Request.manual = True)
  requests.push({requestor: people[1].id, requestee: people[6].id, type: "forbid", manual: true});
  requests.push({requestor: people[20].id, requestee: people[21].id, type: "require", manual: true});

  // Two students with no requests at all (today's UI wrongly flags them red)
  const loners = [people[40].id, people[41].id];
  for (let i = requests.length - 1; i >= 0; i--) {
    if (loners.includes(requests[i].requestor) && !requests[i].manual) requests.splice(i, 1);
  }

  // ---- Site & machine-generated solution ---------------------------------
  const blocks = [
    {name: "Main Wing", room_count: 9, room_capacity: 4},
    {name: "Annex", room_count: 1, room_capacity: 3},
    {name: "Annex Suite", room_count: 1, room_capacity: 4}, // one spare bed overall
  ];

  const rooms = [];
  let roomId = 501;
  for (const b of blocks) {
    for (let i = 1; i <= b.room_count; i++) {
      rooms.push({
        id: roomId++,
        internal_name: `${b.name} #${String(i).padStart(2, "0")}`,
        placed_name: null,
        capacity: b.room_capacity,
        people: [],
      });
    }
  }

  // Fill rooms in cluster order, then hill-climb with swaps like the
  // "Tuned" generators do, so the starting point looks machine-optimised.
  const ordered = clusters.flat().concat(people.map(p => p.id).filter(id => !clusters.flat().includes(id)));
  let r = 0;
  for (const id of ordered) {
    while (rooms[r].people.length >= rooms[r].capacity) r++;
    rooms[r].people.push(id);
  }

  function quickScore() {
    const inv = {};
    rooms.forEach((rm, i) => rm.people.forEach(id => { inv[id] = i; }));
    let total = 0;
    const per = {};
    for (const q of requests) {
      const same = inv[q.requestor] === inv[q.requestee];
      if (q.manual) { if ((q.type === "forbid") === same) total += 1e6; continue; }
      if (q.type !== "attract") continue;
      per[q.requestor] = per[q.requestor] || [0, 0];
      per[q.requestor][0]++;
      if (!same) per[q.requestor][1]++;
    }
    for (const id in per) {
      const [n, f] = per[id];
      total += f / n + (f === n ? 1000 : 0);
    }
    return total;
  }

  function climb() {
    let best = quickScore(), improved = true;
    while (improved) {
      improved = false;
      for (let a = 0; a < rooms.length; a++) for (let b = a + 1; b < rooms.length; b++) {
        const A = rooms[a], B = rooms[b];
        for (let i = 0; i < A.people.length; i++) for (let j = 0; j < B.people.length; j++) {
          [A.people[i], B.people[j]] = [B.people[j], A.people[i]];
          const sc = quickScore();
          if (sc < best - 1e-9) { best = sc; improved = true; }
          else [A.people[i], B.people[j]] = [B.people[j], A.people[i]];
        }
      }
    }
    return best;
  }

  // A few random restarts; keep the best layout found
  let bestLayout = null, bestScore = Infinity;
  for (let restart = 0; restart < 6; restart++) {
    const all = rooms.flatMap(rm => rm.people).sort(() => rand() - 0.5);
    const spare = rooms[rooms.length - 1]; // the spare bed lives in the last room
    rooms.forEach(rm => { rm.people = all.splice(0, rm === spare ? rm.capacity - 1 : rm.capacity); });
    const sc = climb();
    if (sc < bestScore) { bestScore = sc; bestLayout = rooms.map(rm => [...rm.people]); }
  }
  rooms.forEach((rm, i) => { rm.people = bestLayout[i]; });

  // Leave a couple of rough edges for the admin to fix by hand
  function swapPeople(x, y) {
    const rx = rooms.find(rm => rm.people.includes(x)), ry = rooms.find(rm => rm.people.includes(y));
    rx.people[rx.people.indexOf(x)] = y;
    ry.people[ry.people.indexOf(y)] = x;
  }
  swapPeople(people[2].id, people[12].id);

  // A couple of rooms already have real hotel numbers from a previous pass
  rooms[0].placed_name = "214";
  rooms[1].placed_name = "215";

  // ---- Hotel inventory (for the placement mockup) ------------------------
  // Not in the data model yet — this is what a "real hotel rooms" feature
  // would need: room numbers, beds, and which rooms share a connecting door.
  const hotel = {
    name: "Harborview Lodge",
    floors: [
      {
        level: 2,
        rooms: [
          {number: "201", beds: 4, connects: "202"}, {number: "202", beds: 4, connects: "201"},
          {number: "203", beds: 4, connects: "204"}, {number: "204", beds: 4, connects: "203"},
          {number: "205", beds: 3, connects: null},  {number: "206", beds: 4, connects: null, blocked: "Chaperone"},
          {number: "207", beds: 4, connects: "208"}, {number: "208", beds: 4, connects: "207"},
        ],
      },
      {
        level: 3,
        rooms: [
          {number: "211", beds: 4, connects: "212"}, {number: "212", beds: 4, connects: "211"},
          {number: "213", beds: 3, connects: null},  {number: "214", beds: 4, connects: "215"},
          {number: "215", beds: 4, connects: "214"}, {number: "216", beds: 4, connects: null, blocked: "Chaperone"},
          {number: "217", beds: 4, connects: "218"}, {number: "218", beds: 4, connects: "217"},
        ],
      },
    ],
  };

  window.MOCK = {
    solution: {
      id: 37,
      name: "Tuned female rooms generated 2026-09-28 21:14",
      strategy: "Tuned Simulated Annealing",
      gender: "female",
      rooms,
    },
    people,
    requests,
    hotel,
  };
})();
