frappe.pages['ai-chat'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'AI Chat',
		single_column: true
	});

    // We will inject the Vue App container
    page.main.html(`
        <div id="ai-chat-app" class="ai-chat-container">
            <!-- Vue App Mount Point -->
            <div class="chat-glass">
                <div class="chat-header">
                    <h3>Gemini Assistant</h3>
                </div>
                <div class="chat-messages" ref="messagesContainer">
                    <div v-for="(msg, index) in messages" :key="index" :class="['message-row', msg.role]">
                        <div class="message-bubble">
                            <div class="message-content" v-html="parseMarkdown(msg.content)"></div>
                        </div>
                    </div>
                    <div v-if="loading" class="message-row ai">
                        <div class="message-bubble loading">
                            <span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
                        </div>
                    </div>
                </div>
                <div class="chat-input-area">
                    <input type="text" v-model="userInput" @keyup.enter="sendMessage" placeholder="Ask about your ERP data..." :disabled="loading" />
                    <button @click="sendMessage" :disabled="loading || !userInput">
                        Send
                    </button>
                </div>
            </div>
        </div>
    `);

    // Add styles dynamically
    frappe.require('/assets/ai_integration/css/ai-chat.css');

    // Initialize Vue
    if (typeof Vue === 'undefined') {
         frappe.require(['/assets/ai_integration/js/vue.global.prod.js', '/assets/ai_integration/js/marked.umd.js', '/assets/ai_integration/js/purify.min.js'], () => {
             initVue(wrapper);
         });
    } else {
         frappe.require(['/assets/ai_integration/js/marked.umd.js', '/assets/ai_integration/js/purify.min.js'], () => {
             initVue(wrapper);
         });
    }
}

function initVue(wrapper) {
    const { createApp, ref, nextTick, watch } = Vue;

    const app = createApp({
        setup() {
            const processDocumentLinks = (html) => {
                // Regex to find potential document references like "Sales Invoice SINV-0001" or "Invoice-001"
                // It looks for a sequence of words (DocType) followed by a hyphenated ID.
                // It also handles generic "Invoice-001" cases where the DocType might be implied or explicit.
                // We use a broader regex and try to smart-link.
                // Pattern: (DocType) (Name)
                // e.g. "Sales Invoice SINV-2023-001"
                // e.g. "Invoice SINV-001"

                // Let's iterate over common patterns.
                // Basic pattern: \b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s+([A-Z0-9]+-[A-Z0-9-]+)\b
                // This captures "Sales Invoice SINV-001" -> Group 1: Sales Invoice, Group 2: SINV-001

                const docTypePattern = /\b([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*)\s+([A-Z0-9]+-[A-Z0-9-]+)\b/g;

                return html.replace(docTypePattern, (match, p1, p2) => {
                    // p1 is likely the DocType (e.g. "Sales Invoice")
                    // p2 is the Name (e.g. "SINV-001")

                    // Basic validation to avoid false positives (e.g. "Model X-100") - hard to do perfectly without backend check.
                    // But we can assume capital letters for DocType.

                    // Normalize DocType for URL: "Sales Invoice" -> "sales-invoice"
                    const doctypeSlug = p1.toLowerCase().replace(/\s+/g, '-');

                    // Construct URL
                    const url = `/app/${doctypeSlug}/${p2}`;

                    return `<a href="${url}" class="doc-link" target="_blank" title="Open ${p1}">${match}</a>`;
                });
            };

            const parseMarkdown = (content) => {
                if (typeof marked !== 'undefined' && marked.parse) {
                    let rawHtml = marked.parse(content);
                    if (typeof DOMPurify !== 'undefined') {
                        // Allow 'target' and 'class' attributes for our links
                        const cleanHtml = DOMPurify.sanitize(rawHtml, { ADD_ATTR: ['target', 'class'] });
                         return processDocumentLinks(cleanHtml);
                    }
                    return processDocumentLinks(rawHtml);
                }
                return content;
            };

            const messages = ref([
                { role: 'ai', content: 'Hello! I can help you find information in your ERP. What would you like to know?' }
            ]);
            const userInput = ref('');
            const loading = ref(false);
            const messagesContainer = ref(null);

            const scrollToBottom = () => {
                nextTick(() => {
                    const el = document.querySelector('.chat-messages');
                    if (el) el.scrollTop = el.scrollHeight;
                });
            };

            const sendMessage = async () => {
                if (!userInput.value.trim()) return;

                const text = userInput.value;
                messages.value.push({ role: 'user', content: text });
                userInput.value = '';
                loading.value = true;
                scrollToBottom();

                try {
                    const r = await frappe.call({
                        method: 'ai_integration.api.chat.send_message',
                        args: { message: text }
                    });

                    if (r.message && r.message.response) {
                        messages.value.push({ role: 'ai', content: r.message.response });
                    } else if (r.message && r.message.error) {
                         messages.value.push({ role: 'ai', content: 'Error: ' + r.message.error });
                    } else {
                        messages.value.push({ role: 'ai', content: 'Something went wrong.' });
                    }
                } catch (e) {
                    console.error(e);
                    messages.value.push({ role: 'ai', content: 'Connection error.' });
                } finally {
                    loading.value = false;
                    scrollToBottom();
                }
            };

            return {
                messages,
                userInput,
                sendMessage,
                loading,
                messagesContainer,
                parseMarkdown
            };
        }
    });

    app.mount('#ai-chat-app');
}
