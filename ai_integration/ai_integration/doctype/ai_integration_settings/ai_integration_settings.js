frappe.ui.form.on('AI Integration Settings', {
	refresh(frm) {
		frm.fields_dict['generate_embeddings_html'].$wrapper.html(`
			<button class="btn btn-primary btn-sm" id="btn-generate-embeddings">
				Generate Embeddings
			</button>
		`);

		frm.fields_dict['generate_embeddings_html'].$wrapper.find('#btn-generate-embeddings').on('click', () => {
			frappe.confirm('Are you sure you want to generate embeddings for all enabled DocTypes? This might take a while.', () => {
				frappe.call({
					method: 'ai_integration.ai_integration.doctype.ai_integration_settings.ai_integration_settings.generate_all_embeddings',
					freeze: true,
					freeze_message: 'Generating Embeddings...',
					callback: function(r) {
						frappe.msgprint('Embedding generation task started/completed.');
					}
				});
			});
		});
	}
});
