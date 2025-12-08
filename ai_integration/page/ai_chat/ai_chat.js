frappe.pages['ai-chat'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'AI Chat',
        single_column: true
    });

    page.main.html(frappe.render_template('ai_chat', {}));

    const $input = page.main.find('.chat-input');
    const $sendBtn = page.main.find('.btn-send');
    const $history = page.main.find('.chat-history');
    const $intro = page.main.find('.intro-message');

    function appendMessage(text, sender) {
        $intro.hide();
        const wrapperClass = sender === 'user' ? 'user' : 'bot';
        const html = `
			<div class="chat-message ${wrapperClass}">
				<div class="message-bubble">
					${frappe.markdown(text)}
				</div>
			</div>
		`;
        $history.append(html);
        $history.scrollTop($history[0].scrollHeight);
    }

    function showTyping() {
        const html = `
			<div class="chat-message bot typing-indicator-container">
				<div class="typing-indicator">
					Thinking...
				</div>
			</div>
		`;
        $history.append(html);
        $history.scrollTop($history[0].scrollHeight);
    }

    function hideTyping() {
        page.main.find('.typing-indicator-container').remove();
    }

    function sendMessage() {
        const msg = $input.val();
        if (!msg) return;

        appendMessage(msg, 'user');
        $input.val('');
        showTyping();

        frappe.call({
            method: "ai_integration.ai_integration.page.ai_chat.ai_chat.message",
            args: {
                message: msg
            },
            callback: function (r) {
                hideTyping();
                if (r.message) {
                    appendMessage(r.message, 'bot');
                } else {
                    appendMessage("I encountered an error or received no response.", 'bot');
                }
            },
            error: function (r) {
                hideTyping();
                appendMessage("Error communicating with AI.", 'bot');
            }
        });
    }

    $sendBtn.on('click', sendMessage);
    $input.on('keypress', function (e) {
        if (e.which === 13) sendMessage();
    });
}
