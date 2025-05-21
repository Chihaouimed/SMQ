from odoo import models, fields, api
from datetime import datetime

class ActionCorrectiveHistory(models.Model):
    _name = 'action.corrective.history'
    _description = 'Historique des modifications d\'action corrective'

    record_id = fields.Many2one('action', string="Action", required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Utilisateur", required=True)
    model_name = fields.Char(string="Nom du modèle")
    action_type = fields.Selection([
        ('create', 'Création'),
        ('update', 'Mise à jour'),
        ('delete', 'Suppression')
    ], string="Type d'action")
    field_name = fields.Char(string="Champ modifié")
    old_state = fields.Char(string="Ancienne valeur")
    new_state = fields.Char(string="Nouvelle valeur")
    change_date = fields.Datetime(string="Date du changement", default=lambda self: fields.Datetime.now())