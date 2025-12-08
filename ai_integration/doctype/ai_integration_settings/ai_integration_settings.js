frappe.ui.form.on('AI Integration Settings', {
    refresh: function (frm) {
        frm.add_custom_button(__('Generate Embeddings'), function () {
            frappe.call({
                method: 'ai_integration.embedding_engine.generate_embeddings',
                freeze: true,
                freeze_message: __('Generating Embeddings...'),
                callback: function (r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Embeddings generated successfully'),
                            indicator: 'green'
                        });
                    }
                }
            });
        });
    }
});
