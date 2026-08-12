import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { verifyEvent } from "nostr-tools";

const root = new URL("./", import.meta.url);
const envelope = JSON.parse(readFileSync(new URL("events.json", root), "utf8"));
if (envelope.schema !== "vela.stock-buzz-activity-events.v1") {
  throw new Error("unexpected event envelope schema");
}
if (envelope.events.length !== 3 || !envelope.events.every(verifyEvent)) {
  throw new Error("nostr-tools refused a retained Buzz event");
}
const lock = readFileSync(new URL("bun.lock", root));
process.stdout.write(JSON.stringify({
  authority_effect: "none",
  event_ids: envelope.events.map((event) => event.id),
  events_verified: envelope.events.length,
  nostr_tools_version: "2.23.12",
  package_lock_raw_sha256: `sha256:${createHash("sha256").update(lock).digest("hex")}`,
  verifier: "nostr-tools",
  verification_scope: "cross_implementation_signature_only",
}) + "\n");
