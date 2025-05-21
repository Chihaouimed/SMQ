from odoo import models, fields

class SuggestionClient(models.Model):
    _name = 'suggestion.client'
    _description = 'Suggestion Client'

    date_suggestion = fields.Date(string='Date de Suggestion', required=True)
    client_concerne = fields.Many2one('res.partner', string='Client Concerné', required=True)
    type_suggestion = fields.Selection([
        ('parametre1', 'Paramètre 1'),
        ('parametre2', 'Paramètre 2'),
        ('parametre3', 'Paramètre 3'),
    ], string='Type de Suggestion', required=True)
    description_suggestion = fields.Text(string='Description de la Suggestion', required=True)
    receptionnaire_suggestion = fields.Many2one('hr.employee', string='Réceptionnaire de Suggestion', required=True)
    action_associe = fields.Text(string='Action Associée')
    decideur_traitement = fields.Many2one('hr.employee', string='Décideur de Traitement', required=True)
    suggestion_retenue = fields.Selection([
        ('retenue', 'Retenue'),
        ('non_retenue', 'Non Retenue'),
    ], string='Suggestion Retenue ou Non', required=True)
    commentaire_decideur = fields.Text(string='Commentaire du Décideur', required=True)
    piece_jointe = fields.Binary(string='Pièce Jointe')
    plan_action_filename = fields.Char(string="Nom du fichier")
    validation_suggestion = fields.Boolean(string='Validation de Suggestion', default=False)
    client_ids = fields.Many2many('res.partner', string="liste des concernés")

