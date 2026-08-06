// Exhaustive route crawler — hits every page across all datasets and reports non-200s.
const fs = require("fs");
const path = require("path");

const BASE = "http://localhost:3000";
const DATA = path.join(process.cwd(), "public", "data");
const index = JSON.parse(fs.readFileSync(path.join(DATA, "index.json"), "utf8"));

const STATIC = ["/", "/matches", "/predictions", "/clubs", "/players", "/rankings", "/models", "/table", "/methodology"];

async function hit(url) {
  try {
    const r = await fetch(BASE + url, { redirect: "manual" });
    return r.status;
  } catch (e) {
    return "ERR:" + e.message;
  }
}

(async () => {
  const failures = [];
  let count = 0;
  for (const l of index.leagues) {
    for (const s of l.seasons) {
      const q = `?league=${l.id}&season=${s.id}`;
      for (const r of STATIC) {
        const st = await hit(r + q);
        count++;
        if (st !== 200) failures.push([r + q, st]);
      }
      const clubs = JSON.parse(fs.readFileSync(path.join(DATA, l.id, s.id, "clubs.json"), "utf8"));
      for (const c of clubs) {
        const url = `/clubs/${c.code.toLowerCase()}${q}`;
        const st = await hit(url);
        count++;
        if (st !== 200) failures.push([url, st]);
      }
      const players = JSON.parse(fs.readFileSync(path.join(DATA, l.id, s.id, "players.json"), "utf8")).players;
      for (const p of players) {
        const url = `/players/${p.id}${q}`;
        const st = await hit(url);
        count++;
        if (st !== 200) failures.push([url, st]);
      }
      console.log(`done ${l.id}/${s.id} — clubs ${clubs.length}, players ${players.length}`);
    }
  }
  console.log(`\nCrawled ${count} routes. Failures: ${failures.length}`);
  for (const [u, st] of failures) console.log(`  ${st}  ${u}`);
})();
