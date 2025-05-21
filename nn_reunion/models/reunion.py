from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class Reunion(models.Model):
    _name = 'reunion.reunion'
    _description = 'Gestion des réunions'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_reunion desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouvelle Réunion'))

    demandeur_id = fields.Many2one('hr.employee', string='Demandeur de la réunion',
                                   required=True, tracking=True)

    date_reunion = fields.Datetime(string='Date prévisionnelle de la réunion',
                                   required=True, tracking=True)

    type_reunion = fields.Selection([
        ('equipe', 'Réunion d\'équipe'),
        ('client', 'Réunion client'),
        ('projet', 'Réunion de projet'),
        ('departement', 'Réunion de département'),
        ('autre', 'Autre')
    ], string='Type de réunion', required=True, tracking=True)

    lieu_reunion = fields.Char(string='Lieu de la réunion', required=True, tracking=True)

    ordre_jour = fields.Text(string='Ordre du jour', required=True, tracking=True)

    participant_ids = fields.Many2many('hr.employee', string='Liste des participants', tracking=True)

    piece_jointe = fields.Binary(string='Pièce jointe', attachment=True)
    piece_jointe_filename = fields.Char(string='Nom du fichier')

    commentaire = fields.Text(string='Commentaire', tracking=True)

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('confirme', 'Confirmée'),
        ('annule', 'Annulée'),
        ('termine', 'Terminée')
    ], string='État', default='brouillon', tracking=True)
    responsable_id = fields.Many2one('hr.employee', string="Responsable")

    duree_estimee = fields.Float(string='Durée estimée (heures)', default=1.0)

    compte_rendu = fields.Text(string='Compte rendu de réunion', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nouvelle Réunion')) == _('Nouvelle Réunion'):
            vals['name'] = self.env['ir.sequence'].next_by_code('reunion.reunion') or _('Nouvelle Réunion')
        return super(Reunion, self).create(vals)

    def action_confirmer(self):
        for record in self:
            record.state = 'confirme'

    def action_annuler(self):
        for record in self:
            record.state = 'annule'

    def action_terminer(self):
        for record in self:
            record.state = 'termine'

    @api.constrains('date_reunion')
    def _check_date_reunion(self):
        for record in self:
            if record.date_reunion and record.date_reunion < datetime.now():
                raise ValidationError(_("La date de réunion ne peut pas être dans le passé."))
