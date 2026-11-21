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
        // Match Workspace's actual header: logo, language selector, version and Ko-fi.
        let head = document.querySelector(".orki-shell-header");
        if (!head) {
            head = element("header", "orki-shell-header");
            head.setAttribute("role", "banner");
            const brand = link("/workspace", "", "orki-shell-brand");
            const logo = element("img");
            logo.src = "/assets/orkilab/orkilab-logo-dark.svg";
            logo.alt = "OrkiLab";
            brand.append(logo);
            const tools = element("div", "orki-shell-side row");
            const languageLabel = element("label", "orki-shell-language");
            const languageText = element("span", null, "Language");
            languageText.id = "orki-shell-language-label";
            const selector = element("select", "no-i18n");
            selector.id = "orki-shell-language";
            selector.setAttribute("aria-labelledby", "orki-shell-language-label");
            languageLabel.append(languageText, selector);
            const version = element("span", "muted no-i18n", "OrkiLab");
            version.id = "orki-shell-version";
            const support = link("https://ko-fi.com/jorgelf", "♡ Ko-fi · Support OrkiLab", "orki-header-kofi no-i18n");
            support.title = "Voluntary support for the open-source OrkiLab project";
            support.target = "_blank";
            support.rel = "noopener noreferrer";
            tools.append(languageLabel, version, support);
            head.append(brand, tools);
            document.body.insertBefore(head, layout);
            if (typeof I18N !== "undefined" && Array.isArray(I18N.languages)) {
                for (const [code, label] of I18N.languages) selector.add(new Option(label, code));
                selector.value = I18N.lang;
            }
            selector.addEventListener("change", async () => {
                const previous = typeof I18N !== "undefined" ? I18N.lang : "en";
                selector.disabled = true;
                try {
                    const result = await fetch("/api/i18n", {
                        method: "POST", credentials: "same-origin",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({language: selector.value})
                    });
                    if (!result.ok) throw new Error("Could not change language");
                    location.reload();
                } catch (error) {
                    selector.value = previous;
                    selector.disabled = false;
                    const message = document.querySelector(".orki-shell-context-description");
                    if (message) { message.textContent = error.message; message.hidden = false; }
                }
            });
            fetch("/api/workspace/overview", {credentials:"same-origin"}).then(r => r.ok ? r.json() : null).then(info => {
                if (info && info.version) version.textContent = info.version;
            }).catch(() => {});
        }
        const languageText = head.querySelector("#orki-shell-language-label");
        if (languageText) languageText.textContent = typeof I18N !== "undefined" ? I18N.translate("Language") : "Language";
        const selector = head.querySelector("#orki-shell-language");
        if (selector && typeof I18N !== "undefined") selector.value = I18N.lang;
        // Use the same contextual title-and-help pattern as #workspace-context.
        let context = content.querySelector(".orki-shell-workspace-context");
        if (!context) {
            context = element("section", "workspace-context orki-shell-workspace-context");
            const row = element("div", "row");
            const title = element("strong", "no-i18n");
            title.id = "orki-shell-context-title";
            const toggle = element("button");
            toggle.type = "button";
            toggle.id = "orki-shell-context-toggle";
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-controls", "orki-shell-context-description");
            const toggleLabel = element("span");
            toggleLabel.id = "orki-shell-context-toggle-label";
            const info = element("span", null, "ⓘ");
            info.setAttribute("aria-hidden", "true");
            toggle.append(toggleLabel, document.createTextNode(" "), info);
            row.append(title, toggle);
            const description = element("p", "muted no-i18n");
            description.id = "orki-shell-context-description";
            description.hidden = true;
            context.append(row, description);
            content.prepend(context);
            toggle.addEventListener("click", () => {
                const opened = description.hidden;
                description.hidden = !opened;
                toggle.setAttribute("aria-expanded", String(opened));
            });
        }
        const help = {
            en: ["What can I do here?", "Job queue", "See active, waiting and completed training jobs. Pause the queue, reorder pending tasks, monitor progress and review previous results.", "Dataset Studio", "Import images by reference, review datasets, analyze duplicates or blur, compare images and organize selections without deleting originals."],
            es: ["¿Qué puedo hacer aquí?", "Cola de trabajo", "Consulta trabajos en curso, pendientes y terminados. Pausa la cola, cambia el orden de las tareas, supervisa el progreso y revisa el historial.", "Dataset Studio", "Importa imágenes sin copiarlas, revisa datasets, analiza duplicados o desenfoque y compara imágenes sin borrar los archivos originales."],
            pt: ["O que posso fazer aqui?", "Fila de trabalhos", "Veja trabalhos ativos, pendentes e concluídos. Pause a fila, altere a ordem e consulte o progresso e o histórico.", "Dataset Studio", "Importe imagens por referência, reveja datasets e compare imagens sem apagar os originais."],
            fr: ["Que puis-je faire ici ?", "File de travaux", "Consultez les tâches actives, en attente et terminées. Mettez la file en pause et suivez la progression.", "Dataset Studio", "Importez et examinez vos images, détectez les doublons et comparez-les sans supprimer les originaux."],
            de: ["Was kann ich hier tun?", "Auftragswarteschlange", "Laufende, wartende und abgeschlossene Aufgaben ansehen, anhalten, sortieren und den Fortschritt prüfen.", "Dataset Studio", "Bilder importieren, Duplikate prüfen und vergleichen, ohne Originale zu löschen."],
            it: ["Cosa posso fare qui?", "Coda di lavoro", "Controlla i lavori attivi, in attesa e completati. Metti in pausa la coda e verifica l'avanzamento.", "Dataset Studio", "Importa, controlla e confronta le immagini senza eliminare gli originali."],
            ja: ["ここでは何ができますか？", "ジョブキュー", "進行中・待機中・完了したジョブの表示、順序変更、一時停止、進捗確認ができます。", "Dataset Studio", "元画像を削除せずに画像の取り込み、品質チェック、比較ができます。"],
            ko: ["여기서 무엇을 할 수 있나요?", "작업 대기열", "진행 중, 대기 중, 완료된 작업을 확인하고 일시정지, 순서 변경, 진행 상황을 확인하세요.", "Dataset Studio", "원본을 삭제하지 않고 이미지를 가져오고 품질을 확인하고 비교할 수 있습니다."]
        };
        const words = help[locale] || help.en;
        context.querySelector("#orki-shell-context-title").textContent = page === "queue" ? words[1] : words[3];
        context.querySelector("#orki-shell-context-toggle-label").textContent = words[0];
        context.querySelector("#orki-shell-context-description").textContent = page === "queue" ? words[2] : words[4];
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
