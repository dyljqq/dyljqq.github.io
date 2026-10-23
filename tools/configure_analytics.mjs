// Default is read-only. --write configures only the verified beforego.art Web stream/property.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createSign } from "node:crypto";

const property = "properties/560450579";
const stream = `${property}/dataStreams/16188106745`;
const dimensions = ["site_platform", "page_type", "page_app", "page_language", "section", "control_id",
  "control_type", "target_app", "store_campaign", "store_country", "source_ref", "form_id"];
assert.equal(new Set(dimensions).size, dimensions.length);
assert(dimensions.every((name) => /^[a-z][a-z0-9_]{0,39}$/.test(name)));
if (process.argv.includes("--self-test")) {
  console.log("Analytics configuration definitions: 12 unique valid dimensions; fixed Web property and stream.");
  process.exit(0);
}
const write = process.argv.includes("--write");
const credentialPath = process.env.GOOGLE_SERVICE_ACCOUNT_JSON || process.env.GOOGLE_APPLICATION_CREDENTIALS;
if (!credentialPath) throw new Error("Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS to an existing service account credential file.");
const sa = JSON.parse(readFileSync(credentialPath, "utf8"));
const now = Math.floor(Date.now() / 1000);
const b64 = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
const unsigned = b64({ alg: "RS256", typ: "JWT" }) + "." + b64({
  iss: sa.client_email, scope: "https://www.googleapis.com/auth/analytics.edit",
  aud: sa.token_uri, iat: now, exp: now + 3600
});
const assertion = unsigned + "." + createSign("RSA-SHA256").update(unsigned).sign(sa.private_key).toString("base64url");
const authResponse = await fetch(sa.token_uri, {
  method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion }),
  signal: AbortSignal.timeout(20000)
});
const auth = await authResponse.json();
if (!authResponse.ok || !auth.access_token) throw new Error("Google authentication failed: " + (auth.error_description || auth.error || authResponse.status));
async function admin(path, options = {}, version = "v1beta") {
  const response = await fetch(`https://analyticsadmin.googleapis.com/${version}/${path}`, {
    ...options, headers: { Authorization: `Bearer ${auth.access_token}`, "Content-Type": "application/json" },
    signal: AbortSignal.timeout(20000)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(`GA4 ${response.status}: ${result.error?.message || "request failed"}`);
  return result;
}
const dataStream = await admin(stream);
assert.equal(dataStream.type, "WEB_DATA_STREAM");
assert.equal(dataStream.webStreamData?.measurementId, "G-ZHCG565YKK");
assert.equal(dataStream.webStreamData?.firebaseAppId, "1:448278310866:web:6ec382056194132bfa620b");
const [enhanced, existingDimensions, existingKeys] = await Promise.all([
  admin(`${stream}/enhancedMeasurementSettings`, {}, "v1alpha"),
  admin(`${property}/customDimensions?pageSize=200`),
  admin(`${property}/keyEvents?pageSize=200`)
]);
const missing = dimensions.filter((name) => !(existingDimensions.customDimensions || []).some((d) => d.scope === "EVENT" && d.parameterName === name));
const hasKey = (existingKeys.keyEvents || []).some((event) => event.eventName === "app_store_click");
console.log(JSON.stringify({ mode: write ? "write" : "check", property, stream,
  enhancedMeasurementEnabled: !!enhanced.streamEnabled, missingDimensions: missing, appStoreKeyEventExists: hasKey }));
if (!write) process.exit(0);
if (enhanced.streamEnabled) await admin(`${stream}/enhancedMeasurementSettings?updateMask=streamEnabled`, {
  method: "PATCH", body: JSON.stringify({ streamEnabled: false })
}, "v1alpha");
for (const name of missing) await admin(`${property}/customDimensions`, {
  method: "POST", body: JSON.stringify({ parameterName: name, displayName: `Web ${name}`, scope: "EVENT",
    description: "beforego.art website event parameter. See ANALYTICS.md for measurement definitions." })
});
if (!hasKey) await admin(`${property}/keyEvents`, {
  method: "POST", body: JSON.stringify({ eventName: "app_store_click", countingMethod: "ONCE_PER_EVENT" })
});
const [confirmedEnhanced, confirmedDimensions, confirmedKeys] = await Promise.all([
  admin(`${stream}/enhancedMeasurementSettings`, {}, "v1alpha"),
  admin(`${property}/customDimensions?pageSize=200`),
  admin(`${property}/keyEvents?pageSize=200`)
]);
assert.equal(!!confirmedEnhanced.streamEnabled, false);
assert(dimensions.every((name) => confirmedDimensions.customDimensions.some((d) => d.scope === "EVENT" && d.parameterName === name)));
assert(confirmedKeys.keyEvents.some((event) => event.eventName === "app_store_click"));
console.log("Verified: enhanced measurement off; 12 event dimensions registered; app_store_click is a key event.");
