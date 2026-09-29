let messages = [];
let conversationId = null;
let abortController = null;

const chat =              document.getElementById("chat");
const promptInput =       document.getElementById("prompt");
const modelSelect =       document.getElementById("model");
const sendButton =        document.getElementById("sendButton");
const clearButton =       document.getElementById("clearButton");
const stopButton =        document.getElementById("stopButton");
const showStatsCheckbox = document.getElementById("showStats");
const statsModal =        document.getElementById("statsModal");
const statsContent =      document.getElementById("statsContent");
const closeStats =        document.getElementById("closeStats");



// =========================
// Copie compatible HTTP
// =========================

async function copyText(text) {

    if (
        navigator.clipboard &&
        window.isSecureContext
    ) {

        await navigator.clipboard.writeText(text);

        return;
    }


    const textarea =
        document.createElement("textarea");

    textarea.value = text;

    textarea.style.position = "fixed";
    textarea.style.opacity = "0";

    document.body.appendChild(textarea);

    textarea.focus();
    textarea.select();

    const success =
        document.execCommand("copy");

    textarea.remove();

    if (!success) {

        throw new Error(
            "Impossible de copier le texte"
        );
    }
}

// =========================
// Copie riche de la réponse complète
// =========================

function copyRichText(element) {

    const selection =
        window.getSelection();

    const range =
        document.createRange();

    range.selectNodeContents(element);

    selection.removeAllRanges();
    selection.addRange(range);

    try {

        const success =
            document.execCommand("copy");

        if (!success) {

            throw new Error(
                "Impossible de copier la réponse"
            );
        }

    } finally {

        selection.removeAllRanges();

    }
}


// =========================
// Markdown + coloration syntaxique
// =========================

function renderMarkdown(content) {

    const container =
        document.createElement("div");

    container.innerHTML =
        marked.parse(content || "");

    container
        .querySelectorAll("a")
        .forEach(function(link) {

            link.target = "_blank";
            link.rel = "noopener noreferrer";

        });

    container
        .querySelectorAll("pre code")
        .forEach(function(block) {

            const languageClass =
                Array.from(block.classList)
                    .find(function(className) {

                        return className.startsWith(
                            "language-"
                        );

                    });


            if (!languageClass) {
                return;
            }


            const language =
                languageClass.replace(
                    "language-",
                    ""
                );


            if (
                typeof hljs !== "undefined" &&
                hljs.getLanguage(language)
            ) {

                block.innerHTML =
                    hljs.highlight(
                        block.textContent,
                        {
                            language: language
                        }
                    ).value;

                block.classList.add("hljs");
            }

        });
    container
        .querySelectorAll("pre code")
        .forEach(function(block) {

            const languageClass =
                Array.from(block.classList)
                    .find(function(className) {

                        return className.startsWith(
                            "language-"
                        );

                    });

            if (!languageClass) {
                return;
            }

            const pre =
                block.parentElement;

            const wrapper =
                document.createElement("div");

            wrapper.className =
                "code-block-wrapper";

            const copyButton =
                document.createElement("button");

            copyButton.innerText =
                "📋 Copier";

            copyButton.className =
                "code-copy-button";

            pre.parentNode.insertBefore(
                wrapper,
                pre
            );

            wrapper.appendChild(pre);
            wrapper.appendChild(copyButton);

        });

    return container.innerHTML;
}


// =========================
// Affichage message
// =========================

function addMessage(role, content) {

    const div = document.createElement("div");

    div.className = "message " + role;

    const contentDiv =
        document.createElement("div");

    contentDiv.className =
        "message-content";

    contentDiv.innerHTML =
        renderMarkdown(content);

    div.appendChild(contentDiv);

    if (role === "assistant") {

        const copyButton =
            document.createElement("button");

        copyButton.innerText =
            "📋 Copier";

        copyButton.className =
            "copy-button";

        copyButton.addEventListener(
            "click",
            function() {

                try {

                    copyRichText(contentDiv);

                    copyButton.innerText = "✅ Copié";

                    setTimeout(function() {
                        copyButton.innerText = "📋 Copier";
                    }, 1500);

                } catch (error) {

                    console.error(
                        "Erreur copie réponse :",
                        error
                    );

                    alert(
                        "Impossible de copier la réponse."
                    );

                }

            }
        );

        div.appendChild(copyButton);
    }

    chat.appendChild(div);

    chat.scrollTop =
        chat.scrollHeight;

    return contentDiv;
}


// =========================
// Charger les conversations
// =========================

async function loadConversations() {

    const conversationList =
        document.getElementById(
            "conversationList"
        );


    try {

        const response =
            await fetch(
                "/api/conversations"
            );


        if (!response.ok) {

            throw new Error(
                "Erreur HTTP " +
                response.status
            );

        }


        const conversations =
            await response.json();


        conversationList.innerHTML = "";


        const now =
            new Date();

        const todayStart =
            new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate()
            );

        const yesterdayStart =
            new Date(
                todayStart
            );

        yesterdayStart.setDate(
            yesterdayStart.getDate() - 1
        );

        const sevenDaysStart =
            new Date(
                todayStart
            );

        sevenDaysStart.setDate(
            sevenDaysStart.getDate() - 7
        );


        const groups = {
            today: [],
            yesterday: [],
            last7days: [],
            older: []
        };


        conversations.forEach(
            function(conversation) {

                const dateString =
                    conversation.updated_at ||
                    conversation.created_at;

                const conversationDate =
                    new Date(
                        dateString
                    );


                if (
                    conversationDate >=
                    todayStart
                ) {

                    groups.today.push(
                        conversation
                    );

                }
                else if (
                    conversationDate >=
                    yesterdayStart
                ) {

                    groups.yesterday.push(
                        conversation
                    );

                }
                else if (
                    conversationDate >=
                    sevenDaysStart
                ) {

                    groups.last7days.push(
                        conversation
                    );

                }
                else {

                    groups.older.push(
                        conversation
                    );

                }

            }
        );


        function createGroupTitle(
            title
        ) {

            const heading =
                document.createElement(
                    "div"
                );

            heading.className =
                "conversation-group-title";

            heading.innerText =
                title;

            conversationList.appendChild(
                heading
            );

        }


        function renderConversation(
            conversation
        ) {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "conversation-row";


            const button =
                document.createElement(
                    "button"
                );

            button.className =
                "conversation-item";


            if (
                conversationId ===
                conversation.id
            ) {

                button.classList.add(
                    "active"
                );

            }


            button.innerText =
                conversation.title;


            button.addEventListener(
                "click",
                function() {

                    loadConversation(
                        conversation.id
                    );

                }
            );


            const deleteButton =
                document.createElement(
                    "button"
                );

            deleteButton.innerText =
                "⋯";

            deleteButton.className =
                "delete-conversation-button";


            deleteButton.addEventListener(
                "click",
                function(event) {

                    event.stopPropagation();


                    const existingMenu =
                        document.querySelector(
                            ".conversation-menu"
                        );


                    if (existingMenu) {

                        existingMenu.remove();

                    }


                    const menu =
                        document.createElement(
                            "div"
                        );

                    menu.className =
                        "conversation-menu";


                    const renameButton =
                        document.createElement(
                            "button"
                        );

                    renameButton.innerText =
                        "✏️ Renommer";


                    renameButton.addEventListener(
                        "click",
                        async function(event) {

                            event.stopPropagation();


                            const newTitle =
                                prompt(
                                    "Nouveau nom de la conversation :",
                                    conversation.title
                                );


                            if (
                                newTitle === null ||
                                !newTitle.trim()
                            ) {

                                return;

                            }


                            try {

                                const response =
                                    await fetch(
                                        "/api/conversations/" +
                                        conversation.id,
                                        {
                                            method: "PUT",

                                            headers: {
                                                "Content-Type":
                                                    "application/json"
                                            },

                                            body: JSON.stringify({
                                                title:
                                                    newTitle.trim()
                                            })
                                        }
                                    );


                                if (!response.ok) {

                                    throw new Error(
                                        "Erreur HTTP " +
                                        response.status
                                    );

                                }


                                menu.remove();

                                await loadConversations();

                            }
                            catch (error) {

                                console.error(
                                    "Erreur renommage conversation :",
                                    error
                                );

                                alert(
                                    "Impossible de renommer la conversation."
                                );

                            }

                        }
                    );


                    const separator =
                        document.createElement(
                            "div"
                        );

                    separator.className =
                        "conversation-menu-separator";


                    const deleteButtonMenu =
                        document.createElement(
                            "button"
                        );

                    deleteButtonMenu.innerText =
                        "🗑️ Supprimer";


                    deleteButtonMenu.addEventListener(
                        "click",
                        async function(event) {

                            event.stopPropagation();

                            menu.remove();


                            const confirmed =
                                confirm(
                                    "Supprimer cette conversation ?"
                                );


                            if (!confirmed) {

                                return;

                            }


                            try {

                                const response =
                                    await fetch(
                                        "/api/conversations/" +
                                        conversation.id,
                                        {
                                            method: "DELETE"
                                        }
                                    );


                                if (!response.ok) {

                                    throw new Error(
                                        "Erreur HTTP " +
                                        response.status
                                    );

                                }


                                if (
                                    conversationId ===
                                    conversation.id
                                ) {

                                    clearChat();

                                }


                                await loadConversations();

                            }
                            catch (error) {

                                console.error(
                                    "Erreur suppression conversation :",
                                    error
                                );

                                alert(
                                    "Impossible de supprimer la conversation."
                                );

                            }

                        }
                    );


                    menu.appendChild(
                        renameButton
                    );

                    menu.appendChild(
                        separator
                    );

                    menu.appendChild(
                        deleteButtonMenu
                    );


                    row.appendChild(
                        menu
                    );

                }
            );


            row.appendChild(
                button
            );

            row.appendChild(
                deleteButton
            );


            conversationList.appendChild(
                row
            );

        }


        if (
            groups.today.length > 0
        ) {

            createGroupTitle(
                "Aujourd’hui"
            );

            groups.today.forEach(
                renderConversation
            );

        }


        if (
            groups.yesterday.length > 0
        ) {

            createGroupTitle(
                "Hier"
            );

            groups.yesterday.forEach(
                renderConversation
            );

        }


        if (
            groups.last7days.length > 0
        ) {

            createGroupTitle(
                "7 derniers jours"
            );

            groups.last7days.forEach(
                renderConversation
            );

        }


        if (
            groups.older.length > 0
        ) {

            createGroupTitle(
                "Plus ancien"
            );

            groups.older.forEach(
                renderConversation
            );

        }
        
    }
    catch (error) {

        console.error(
            "Erreur chargement conversations :",
            error
        );

    }
}


// =========================
// Affichage statistiques
// =========================

function displayStats(stats) {

    statsContent.innerHTML = `

        <div class="stats-row">
            <span class="stats-label">Modèle</span>
            <span>${stats.model}</span>
        </div>

        <div class="stats-row">
            <span class="stats-label">Tokens prompt</span>
            <span>${stats.prompt_tokens}</span>
        </div>

        <div class="stats-row">
            <span class="stats-label">Tokens générés</span>
            <span>${stats.generated_tokens}</span>
        </div>

        <div class="stats-row">
            <span class="stats-label">Tokens total</span>
            <span>${stats.total_tokens}</span>
        </div>

        <div class="stats-row">
            <span class="stats-label">Temps prompt</span>
            <span>${stats.prompt_duration} s</span>
        </div>

        <div class="stats-row">
            <span class="stats-label">Temps génération</span>
            <span>${stats.generation_duration} s</span>
        </div>

        <div class="stats-row">
            <span class="stats-label">Temps total</span>
            <span>${stats.total_duration} s</span>
        </div>

        <div class="stats-row">
            <span class="stats-label">Vitesse</span>
            <span>${stats.tokens_per_second} tok/s</span>
        </div>
    `;

    statsModal.classList.remove("hidden");
}


// =========================
// Charger une conversation
// =========================

async function loadConversation(id) {

    try {

        const response =
            await fetch(
                "/api/conversations/" + id
            );


        if (!response.ok) {

            throw new Error(
                "Erreur HTTP " +
                response.status
            );

        }


        const conversation =
            await response.json();


        // =========================
        // Mettre à jour la conversation active
        // =========================

        conversationId =
            conversation.id;

        await loadConversations();


        // =========================
        // Recharger les messages
        // =========================

        messages = [];


        chat.innerHTML = "";


        conversation.messages.forEach(
            function(message) {

                messages.push({
                    role: message.role,
                    content: message.content
                });


                addMessage(
                    message.role,
                    message.content
                );

            }
        );


        chat.scrollTop =
            chat.scrollHeight;


        promptInput.focus();

    }
    catch (error) {

        console.error(
            "Erreur chargement conversation :",
            error
        );

    }
}


// =========================
// Envoyer un message
// =========================

async function sendMessage() {

    const prompt = promptInput.value.trim();

    if (!prompt) {
        return;
    }


    abortController =
        new AbortController();

    const model = modelSelect.value;


    // =========================
    // Créer une conversation
    // si nécessaire
    // =========================

    if (conversationId === null) {

        const conversationResponse =
            await fetch(
                "/api/conversations",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        title: prompt.substring(0, 50)
                    })
                }
            );


        if (!conversationResponse.ok) {

            throw new Error(
                "Impossible de créer la conversation"
            );

        }


        const conversation =
            await conversationResponse.json();


        conversationId =
            conversation.id;

        await loadConversations();
    }


    promptInput.value = "";

    sendButton.disabled = true;
    stopButton.disabled = false;


    addMessage(
        "user",
        prompt
    );


    messages.push({
        role: "user",
        content: prompt
    });


    const assistantMessage =
        addMessage(
            "assistant",
            "⏳ Génération en cours"
        );

    let loadingDots = 0;

    const loadingInterval =
        setInterval(function() {

            loadingDots =
                (loadingDots + 1) % 4;

            assistantMessage.innerText =
                "⏳ Génération en cours" +
                ".".repeat(loadingDots);

        }, 400);

    await new Promise(resolve => setTimeout(resolve, 100));

    try {

        const response =
            await fetch("/ask", {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    signal:
                        abortController.signal,

                    body: JSON.stringify({
                        messages: messages,
                        model: model,
                        conversation_id:
                            conversationId
                    })
                }
            );


        if (!response.ok) {

            throw new Error(
                "Erreur HTTP " +
                response.status
            );

        }


        const reader =
            response.body.getReader();

        const decoder =
            new TextDecoder();


        let buffer = "";

        let fullResponse = "";

        let stats = null;


        while (true) {

            const result =
                await reader.read();


            if (result.done) {
                break;
            }


            buffer += decoder.decode(
                result.value,
                {
                    stream: true
                }
            );


            const lines =
                buffer.split("\n");


            buffer =
                lines.pop();


            for (const line of lines) {

                if (!line.trim()) {
                    continue;
                }


                const data =
                    JSON.parse(line);

                if (data.type === "content") {

                    clearInterval(loadingInterval);

                    fullResponse +=
                        data.content;

                    assistantMessage.innerHTML =
                        renderMarkdown(
                            fullResponse
                        );
                    chat.scrollTop =
                        chat.scrollHeight;
                }


                if (data.type === "stats") {

                    stats = data;
                }


                if (data.type === "error") {

                    throw new Error(
                        data.error
                    );
                }
            }
        }


        // =========================
        // Dernier paquet éventuel
        // =========================

        if (buffer.trim()) {

            const data =
                JSON.parse(buffer);


            if (data.type === "content") {

                fullResponse +=
                    data.content;

                assistantMessage.innerHTML =
                    renderMarkdown(
                        fullResponse
                    );
            }


            if (data.type === "stats") {

                stats = data;
            }


            if (data.type === "error") {

                throw new Error(
                    data.error
                );
            }
        }


        // =========================
        // Ajouter réponse à l'historique
        // =========================

        messages.push({
            role: "assistant",
            content: fullResponse
        });


        // =========================
        // Afficher statistiques
        // =========================

        if (
            showStatsCheckbox.checked &&
            stats
        ) {

            displayStats(stats);
        }

    } catch (error) {

        if (error.name === "AbortError") {

            return;
        }

        assistantMessage.innerText =
            "❌ Erreur : " +
            error.message;

    }
    finally {

        sendButton.disabled = false;
        stopButton.disabled = true;

        promptInput.focus();
    }
}


// =========================
// Nouvelle conversation
// =========================

function clearChat() {

    messages = [];

    conversationId = null;

    chat.innerHTML = "";

    promptInput.focus();
}


// =========================
// Fermer statistiques
// =========================

function closeStatsModal() {

    statsModal.classList.add("hidden");
}


stopButton.addEventListener(
    "click",
    async function() {

        if (abortController) {

            abortController.abort();
        }

        try {

            await fetch(
                "/cancel",
                {
                    method: "POST"
                }
            );

        } catch (error) {

            console.error(
                "Erreur lors de l'annulation :",
                error
            );

        }
    }
);


sendButton.addEventListener(
    "click",
    sendMessage
);


clearButton.addEventListener(
    "click",
    clearChat
);


closeStats.addEventListener(
    "click",
    closeStatsModal
);


statsModal.addEventListener(
    "click",
    function(event) {

        if (event.target === statsModal) {

            closeStatsModal();
        }

    }
);


// =========================
// Ctrl + Entrée
// =========================

promptInput.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter" &&
            event.ctrlKey
        ) {

            event.preventDefault();

            sendMessage();
        }

    }
);


document
    .getElementById("newConversationButton")
    .addEventListener(
        "click",
        function() {

            clearChat();

        }
    );

// =========================
// Copier les blocs de code
// =========================

chat.addEventListener(
    "click",
    function(event) {

        if (!event.target.classList.contains("code-copy-button")) {
            return;
        }

        const wrapper =
            event.target.closest(".code-block-wrapper");

        if (!wrapper) {
            return;
        }

        const code =
            wrapper.querySelector("pre code");

        if (!code) {
            return;
        }

        copyText(
            code.innerText
        ).then(function() {

            event.target.innerText = "✅ Copié";

            setTimeout(function() {
                event.target.innerText = "📋 Copier";
            }, 1500);

        }).catch(function(error) {

            console.error(
                "Erreur copie code :",
                error
            );

        });

    }
);

// Fermer le menu conversation en cliquant ailleurs

document.addEventListener(
    "click",
    function(event) {

        if (
            event.target.closest(
                ".conversation-menu"
            ) ||
            event.target.closest(
                ".delete-conversation-button"
            )
        ) {
            return;
        }

        const menu =
            document.querySelector(
                ".conversation-menu"
            );

        if (menu) {
            menu.remove();
        }

    }
);

loadConversations();