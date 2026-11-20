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
                    opener.postMessage({type:"orkilab.result",token,prompt:converted.output}, origin);
                } catch (error) {
                    opener.postMessage({type:"orkilab.result",token,error:String(error.message || error)}, origin);
                }
            });
            opener.postMessage({type:"orkilab.ready",token},origin);
        }
    });
}
