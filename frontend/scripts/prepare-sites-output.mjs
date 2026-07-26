import { readdir, readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "server" || entry.name === ".openai") continue;
      files.push(...(await collectFiles(absolute)));
    } else if (!entry.name.endsWith(".map")) {
      files.push(absolute);
    }
  }
  return files;
}

const files = await collectFiles(dist);
const assets = {};
for (const file of files) {
  const relative = path.relative(dist, file).replaceAll("\\", "/");
  const route = relative === "index.html" ? "/" : `/${relative}`;
  assets[route] = {
    body: (await readFile(file)).toString("base64"),
    contentType:
      contentTypes[path.extname(file).toLowerCase()] ??
      "application/octet-stream",
  };
}
assets["/index.html"] = assets["/"];

const worker = `const assets = ${JSON.stringify(assets)};

function decodeBase64(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    }
    const url = new URL(request.url);
    const asset = assets[url.pathname] ?? assets["/"];
    const immutable = url.pathname.startsWith("/assets/");
    return new Response(
      request.method === "HEAD" ? null : decodeBase64(asset.body),
      {
        status: 200,
        headers: {
          "Content-Type": asset.contentType,
          "Cache-Control": immutable
            ? "public, max-age=31536000, immutable"
            : "no-cache",
          "X-Content-Type-Options": "nosniff",
        },
      },
    );
  },
};
`;

await mkdir(path.join(dist, "server"), { recursive: true });
await writeFile(path.join(dist, "server", "index.js"), worker, "utf8");
await mkdir(path.join(dist, ".openai"), { recursive: true });
await writeFile(
  path.join(dist, ".openai", "hosting.json"),
  await readFile(path.join(root, ".openai", "hosting.json")),
);
