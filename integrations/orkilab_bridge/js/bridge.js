import { app } from "../../scripts/app.js";

// A dedicated ComfyUI browser tab is used, never a user's existing editor tab.
const params = new URLSearchParams(location.hash.slice(1));
const token = params.get("orkilab_bridge");
const origin = params.get("origin");
let valid = false;
try {
    const u = new URL(origin);
    valid = u.origin === origin && ["http:", "https:"].includes(u.protocol) &&
        ["127.0.0.1", "localhost", "[::1]"].includes(u.hostname);
} catch (_) {}
if (valid && /^[a-f0-9]{32}$/.test(token || "") && window.opener) {
    app.registerExtension({
        name: "OrkiLab.Bridge",
        async setup() {
            let consumed = false;
            const opener = window.opener;
            window.addEventListener("message", async event => {
                if (consumed || event.source !== opener || event.origin !== origin ||
                    event.data?.token !== token || event.data?.type !== "orkilab.convert") return;
                consumed = true;
                try {
                    if (!event.data.graph || !Array.isArray(event.data.graph.nodes)) throw Error("Invalid visual graph");
                    // Reject missing node types rather than silently accepting placeholders.
                    await app.loadGraphData(event.data.graph, true, false);
                    const converted = await app.graphToPrompt();
                    if (!converted?.output || !Object.keys(converted.output).length) throw Error("No executable nodes returned");
                    // ComfyUI or custom-node widgets can return functions, proxies and
                    // other non-cloneable objects. Cross-window messages must carry
                    // JSON-only API prompt data, not live editor objects.
                    let prompt;
                    try {
                        const serialized = JSON.stringify(converted.output, (_key, value) => {
                            if (typeof value === "function" || typeof value === "symbol" || typeof value === "bigint") {
                                throw Error("Unsupported non-JSON value in converted prompt");
                            }
                            return value;
                        });
                        if (!serialized) throw Error("Empty converted prompt");
                        prompt = JSON.parse(serialized);
                    } catch (error) {
                        throw Error("Cannot serialize ComfyUI prompt: " + String(error.message || error));
                    }
                    if (!prompt || typeof prompt !== "object" || Array.isArray(prompt) || !Object.keys(prompt).length) {
                        throw Error("Invalid converted API prompt");
                    }
                    opener.postMessage({type:"orkilab.result",token,prompt}, origin);
                } catch (error) {
                    const message = "Bridge conversion failed: " + String(error?.message || error);
                    try {
                        opener.postMessage({type:"orkilab.result",token,error:message}, origin);
                    } catch (sendError) {
                        console.error("OrkiLab Bridge could not return conversion error", sendError, message);
                    }
                }
            });
            opener.postMessage({type:"orkilab.ready",token},origin);
        }
    });
}
