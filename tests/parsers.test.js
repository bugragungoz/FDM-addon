// Tests for the add-on's JavaScript parsers. Run from the repository root: node --test tests/parsers.test.js
//
// FDM loads msparser.js and msbatchparser.js as plain scripts with launchPythonScript() among its
// globals; here each one runs in its own context with a stand-in for that function.

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ADDON = path.join(__dirname, "..", "fdm-croxz");

function loadParser(file, name, pythonResult) {
  const context = {
    console: { log() {}, error() {} },
    calls: [],
    launchPythonScript(requestId, interactive, script, args) {
      context.calls.push({ script, args });
      return Promise.resolve(pythonResult);
    },
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ADDON, file), "utf8"), context, { filename: file });
  return { parser: vm.runInContext(name, context), context };
}

test("the media parser takes media sites and streams and leaves files to FDM", () => {
  const { parser } = loadParser("msparser.js", "msParser");

  assert.strictEqual(parser.isSupportedSource("https://www.youtube.com/watch?v=abc123"), true);
  assert.strictEqual(parser.isSupportedSource("https://youtu.be/abc123"), true);
  assert.strictEqual(parser.isSupportedSource("https://cdn.example.com/live/master.m3u8"), true);
  assert.strictEqual(parser.isSupportedSource("https://example.com/files/setup.exe"), false);
  assert.strictEqual(parser.isSupportedSource("https://example.com/news"), false);
});

test("the media parser checks content types for pages it does not know", () => {
  const { parser } = loadParser("msparser.js", "msParser");
  const check = (url, contentType) => parser.isPossiblySupportedSource({ url, contentType });

  assert.strictEqual(check("https://example.com/watch", "video/mp4"), true);
  assert.strictEqual(check("https://example.com/live", "application/vnd.apple.mpegurl"), true);
  assert.strictEqual(check("https://example.com/download", "application/octet-stream"), false);
  assert.strictEqual(check("https://example.com/news", "text/html"), false);
  assert.strictEqual(check("https://vimeo.com/123", "text/html"), true);
  assert.strictEqual(check("ftp://example.com/a", "video/mp4"), false);
});

test("the media parser hands the bridge's JSON to FDM", async () => {
  const output = JSON.stringify({ id: "abc123", title: "Song", formats: [{ url: "https://x/1" }] });
  const { parser, context } = loadParser("msparser.js", "msParser", { exitCode: 0, output });

  const result = await parser.parse({ url: "https://www.youtube.com/watch?v=abc123", requestId: 1, interactive: true });

  assert.deepStrictEqual(JSON.parse(JSON.stringify(context.calls)), [
    { script: "croxz_bridge.py", args: ["extract", "https://www.youtube.com/watch?v=abc123"] },
  ]);
  assert.strictEqual(result.title, "Song");
  assert.strictEqual(result.webpage_url, "https://www.youtube.com/watch?v=abc123");
});

test("the media parser reports the bridge's error", async () => {
  const output = JSON.stringify({ error: "yt-dlp not found. Install it for media extraction support." });
  const { parser } = loadParser("msparser.js", "msParser", { exitCode: 0, output });

  await assert.rejects(
    parser.parse({ url: "https://www.youtube.com/watch?v=abc123", requestId: 1, interactive: true }),
    (error) => /yt-dlp not found/.test(error.error) && error.isParseError === true);
});

test("the playlist parser takes playlist pages only", () => {
  const { parser } = loadParser("msbatchparser.js", "msBatchVideoParser");

  assert.strictEqual(parser.isSupportedSource("https://www.youtube.com/playlist?list=PL1"), true);
  assert.strictEqual(parser.isSupportedSource("https://www.youtube.com/@someone/videos"), true);
  assert.strictEqual(parser.isSupportedSource("https://www.youtube.com/watch?v=abc123"), false);
});

test("the playlist parser keeps entries that have a URL", async () => {
  const output = JSON.stringify({
    _type: "playlist",
    title: "Mix",
    entries: [{ url: "https://www.youtube.com/watch?v=one", title: "First" }, { title: "No URL" }],
  });
  const { parser } = loadParser("msbatchparser.js", "msBatchVideoParser", { exitCode: 0, output });

  const result = await parser.parse({ url: "https://www.youtube.com/playlist?list=PL1", requestId: 1, interactive: true });

  assert.strictEqual(result.entries.length, 1);
  assert.strictEqual(result.entries[0].url, "https://www.youtube.com/watch?v=one");
});
