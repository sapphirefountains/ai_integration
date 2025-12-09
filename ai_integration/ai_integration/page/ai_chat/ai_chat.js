frappe.pages['ai-chat'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'AI Chat',
		single_column: true
	});

    // Load Vue 3 from CDN (or local if preferred, but CDN is quick for this context)
    // Using an ES module approach or global script

    // We will inject the Vue App container
    $(wrapper).find('.layout-main-section').html(`
        <div id="ai-chat-app" class="ai-chat-container">
            <!-- Vue App Mount Point -->
            <div class="chat-glass">
                <div class="chat-header">
                    <h3>Gemini Assistant</h3>
                </div>
                <div class="chat-messages" ref="messagesContainer">
                    <div v-for="(msg, index) in messages" :key="index" :class="['message-row', msg.role]">
                        <div class="message-bubble">
                            <div class="message-content">{{ msg.content }}</div>
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

    // Add styles dynamically or via CSS file
    frappe.require('/assets/ai_integration/css/ai_chat.css');

    // Initialize Vue
    // Since we are in standard desk JS, we can use a library loader or just assume Vue is available if we load it.
    // Frappe v15 usually bundles Vue 3. Let's try to use the global Vue or load it.

    if (typeof Vue === 'undefined') {
         frappe.require('https://unpkg.com/vue@3/dist/vue.global.prod.js', () => {
             initVue(wrapper);
         });
    } else {
        initVue(wrapper);
    }
}

function initVue(wrapper) {
    const { createApp, ref, nextTick, watch } = Vue;

    const app = createApp({
        setup() {
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
                messagesContainer
            };
        }
    });

    app.mount('#ai-chat-app');
}
