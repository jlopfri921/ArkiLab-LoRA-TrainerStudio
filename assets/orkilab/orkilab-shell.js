/* Shared, non-destructive OrkiLab navigation chrome for standalone Workspace tools.
   Never rewrites queue controls, image controls or their listeners. */
(function () {
    "use strict";
    const routes = [
        ["overview", "/workspace#overview"],
        ["projects", "/workspace#projects"],
        ["engines", "/workspace#engines"],
        ["datasets", "/workspace/datasets"],
        ["gpu", "/workspace#gpu-manager"],
        ["queue", "/queue"],
        ["comfy", "/workspace/comfyui"]
    ];
    const names = {
        en: ["Workspace", "Dashboard", "Projects", "Training engines", "Dataset Studio", "GPU Manager", "Job queue", "ComfyUI Zone", "Local AI workspace", "Open-source · Local-first", "Support OrkiLab"],
        es: ["Espacio de trabajo", "Panel general", "Proyectos", "Entrenadores", "Dataset Studio", "Gestor GPU", "Cola de trabajo", "Zona ComfyUI", "Entorno de IA local", "Código abierto · Primero local", "Apoya OrkiLab"],
        pt: ["Área de trabalho", "Painel geral", "Projetos", "Treinadores", "Dataset Studio", "Gestor GPU", "Fila de trabalhos", "Zona ComfyUI", "Área de IA local", "Código aberto · Local", "Apoiar OrkiLab"],
        fr: ["Espace de travail", "Tableau de bord", "Projets", "Entraîneurs", "Dataset Studio", "Gestion GPU", "File de travaux", "Zone ComfyUI", "Espace IA local", "Code ouvert · Local", "Soutenir OrkiLab"],
        de: ["Arbeitsbereich", "Übersicht", "Projekte", "Trainer", "Dataset Studio", "GPU-Manager", "Auftragswarteschlange", "ComfyUI-Bereich", "Lokaler KI-Arbeitsbereich", "Open Source · Lokal", "OrkiLab unterstützen"],
        it: ["Spazio di lavoro", "Dashboard", "Progetti", "Trainer", "Dataset Studio", "Gestione GPU", "Coda lavori", "Zona ComfyUI", "Spazio IA locale", "Open source · Locale", "Sostieni OrkiLab"],
        ja: ["ワークスペース", "ダッシュボード", "プロジェクト", "トレーナー", "Dataset Studio", "GPU管理", "ジョブキュー", "ComfyUIゾーン", "ローカルAI", "オープンソース・ローカル", "OrkiLabを支援"],
        ko: ["작업 공간", "대시보드", "프로젝트", "트레이너", "Dataset Studio", "GPU 관리자", "작업 대기열", "ComfyUI 영역", "로컬 AI", "오픈 소스 · 로컬 우선", "OrkiLab 후원"]
    };
    function element(tag, cls, value) {
        const node = document.createElement(tag);
        if (cls) node.className = cls;
        if (value !== undefined) node.textContent = value;
        return node;
    }
    function link(to, label, cls) {
        const a = element("a", cls, label);
        a.href = to;
        return a;
    }
    function render() {
        const page = location.pathname === "/queue" ? "queue" : "datasets";
        const nav = document.querySelector(page === "queue" ? ".queue-sidebar" : ".studio-navigation");
        const content = document.querySelector(page === "queue" ? ".queue-shell .wrap" : ".studio-content");
        const layout = document.querySelector(page === "queue" ? ".queue-shell" : ".studio-layout");
        if (!nav || !content || !layout) return;
        const locale = typeof I18N !== "undefined" && names[I18N.lang] ? I18N.lang : "en";
        const t = names[locale];
        document.body.classList.add("orki-standalone-shell");
        let head = document.querySelector(".orki-shell-header");
        if (!head) {
            head = element("header", "orki-shell-header");
            head.setAttribute("role", "banner");
            const brand = link("/workspace", "", "orki-shell-brand");
            const logo = element("img");
            logo.src = "/assets/orkilab/orkilab-logo-dark.svg";
            logo.alt = "OrkiLab";
            brand.append(logo);
            const tools = element("div", "orki-shell-side");
            const workspace = link("/workspace", t[0], "orki-shell-home");
            const support = link("https://ko-fi.com/jorgelf", t[10], "orki-shell-support");
            support.target = "_blank";
            support.rel = "noopener noreferrer";
            tools.append(workspace, support);
            head.append(brand, tools);
            document.body.insertBefore(head, layout);
        } else {
            const home = head.querySelector(".orki-shell-home");
            const support = head.querySelector(".orki-shell-support");
            if (home) home.textContent = t[0];
            if (support) support.textContent = t[10];
        }
        nav.setAttribute("aria-label", t[0]);
        nav.replaceChildren(element("span", "nav-heading", t[0]));
        routes.forEach(([id, to], idx) => {
            const a = link(to, t[idx + 1]);
            if (id === page) a.setAttribute("aria-current", "page");
            nav.append(a);
        });
        let footer = content.querySelector(".orki-shell-footer");
        if (!footer) {
            footer = element("footer", "orki-shell-footer");
            content.append(footer);
        }
        footer.replaceChildren();
        const line = element("span", null, "OrkiLab · " + t[9] + " · ");
        const back = link("/workspace", t[0]);
        footer.append(line, back);
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render);
    else render();
    document.addEventListener("orkilab:language-changed", render);
})();
