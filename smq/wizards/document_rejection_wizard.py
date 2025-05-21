from odoo import models, fields, api
from odoo.exceptions import UserError

class DocumentRejectionWizard(models.TransientModel):
    _name = 'document.rejection.wizard'
    _description = "Assistant de rejet"

    documentation_id = fields.Many2one('documentation', string="Document concerné")
    raison = fields.Text(string="Raison du rejet", required=True)

    def action_confirmer_rejet(self):
        if not self.raison:
            raise UserError("Veuillez indiquer la raison du rejet.")
        # Action to save the varibles into document_id
        self.documentation_id.write({
            'state': 'rejected',
            'raison_rejet':self.raison,
            'rejected':True,
        })
