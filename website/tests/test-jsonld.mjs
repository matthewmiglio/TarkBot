// Validates the JSON-LD that actually ships, not the source that builds it.
//
//   npx next build && node tests/test-jsonld.mjs
//
// Checks the failure modes that are invisible in review and silent in production:
// an @id reference with no node behind it, a relative URL, a date that is not
// ISO-8601, a @type that lost its PascalCase.
//
// ponytail: reads the prerendered HTML instead of importing lib/jsonld.ts, so
// there is no ts-node, no loader and no module-resolution wiring to keep alive.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const HTML = ".next/server/app/index.html";

let html;
try {
  html = readFileSync(HTML, "utf8");
} catch {
  console.error(`${HTML} not found. Run \`npx next build\` first.`);
  process.exit(1);
}

const match = html.match(
  /<script type="application\/ld\+json">(.*?)<\/script>/s,
);
assert.ok(match, "no application/ld+json script in the rendered home page");

const graph = JSON.parse(match[1]);
assert.equal(graph["@context"], "https://schema.org");
assert.ok(Array.isArray(graph["@graph"]), "@graph must be an array");

const nodes = graph["@graph"];
const defined = new Set(nodes.map((n) => n["@id"]));

// Every {"@id": x} used as a reference has a node defining x. This is the check
// that catches primaryImageOfPage pointing at an ImageObject nobody wrote.
const referenced = [];
(function walk(value) {
  if (Array.isArray(value)) return value.forEach(walk);
  if (!value || typeof value !== "object") return;
  const keys = Object.keys(value);
  if (keys.length === 1 && keys[0] === "@id") referenced.push(value["@id"]);
  else Object.values(value).forEach(walk);
})(nodes);

for (const id of referenced) {
  assert.ok(defined.has(id), `@id reference "${id}" has no node defining it`);
}

for (const node of nodes) {
  const id = node["@id"] ?? "(anonymous)";
  assert.match(node["@type"], /^[A-Z][A-Za-z]+$/, `${id}: bad @type`);
  assert.ok(id.startsWith("https://"), `${id}: @id must be an absolute URL`);

  for (const key of ["url", "contentUrl", "thumbnailUrl", "embedUrl", "downloadUrl"]) {
    if (node[key] !== undefined) {
      assert.ok(
        String(node[key]).startsWith("https://"),
        `${id}: ${key} is not an absolute https URL`,
      );
    }
  }

  for (const key of ["datePublished", "dateModified", "uploadDate"]) {
    if (node[key] !== undefined) {
      assert.ok(
        !Number.isNaN(Date.parse(node[key])),
        `${id}: ${key} is not a parseable ISO-8601 date`,
      );
    }
  }

  for (const url of node.sameAs ?? []) {
    assert.ok(url.startsWith("https://"), `${id}: sameAs entry ${url} is not https`);
  }
}

// The nodes the page is pointless without.
for (const type of ["Organization", "WebSite", "WebPage", "SoftwareApplication"]) {
  assert.ok(
    nodes.some((n) => n["@type"] === type),
    `graph is missing its ${type} node`,
  );
}

console.log(
  `ok — ${nodes.length} nodes, ${referenced.length} @id references all resolve`,
);
