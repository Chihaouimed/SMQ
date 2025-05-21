from odoo import models, fields

class RecommandationIAWizard(models.TransientModel):
    _name = 'recommandation.ia.wizard'
    _description = "Fenêtre des Recommandations IA"

    recommandation_ia = fields.Text("Recommandation", readonly=True)
    proposition_ia = fields.Text("Proposition", readonly=True)
