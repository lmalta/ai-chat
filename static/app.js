let messages = [];
let conversationId = null;


const chat = document.getElementById("chat");
const promptInput = document.getElementById("prompt");
const modelSelect = document.getElementById("model");
const sendButton = document.getElementById("sendButton");
const clearButton = document.getElementById("clearButton");

const showStatsCheckbox =
    document.getElementById("showStats");

const statsModal =
    document.getElementById("statsModal");

const statsContent =
    document.getElementById("statsContent");

const closeStats =
    document.getElementById("closeStats");


// =========================
// Affichage message
// =========================

function addMessage(role, content) {

    const div = document.createElement("div");

    div.className = "message " + role;

    div.innerText = content;

    chat.appendChild(div);

    chat.scrollTop = chat.scrollHeight;

    return div;
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


        conversations.forEach(
            function(conversation) {

                const button =
                    document.createElement(
                        "button"
                    );


                button.className =
                    "conversation-item";


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


                conversationList.appendChild(
                    button
                );

            }
        );

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
// Envoyer un message
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

async function sendMessage() {

    const prompt =
        promptInput.value.trim();

    if (!prompt) {
        return;
    }


    const model =
        modelSelect.value;


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
            ""
        );


    try {

        const response =
            await fetch(
                "/ask",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

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

                    fullResponse +=
                        data.content;

                    assistantMessage.innerText =
                        fullResponse;

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

                assistantMessage.innerText =
                    fullResponse;
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

    }
    catch (error) {

        assistantMessage.innerText =
            "❌ Erreur : " +
            error.message;

    }
    finally {

        sendButton.disabled = false;

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

loadConversations();