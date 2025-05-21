from odoo import models, fields, api


class SousActions(models.Model):
    _name = 'sous.actions'
    _description = 'Sous-actions'

    action_id = fields.Many2one('action', string="Action associée")
    act_id = fields.Many2one('action', string='action', related='action_id')
    numero_sequentiel = fields.Char(
        string="Numéro Séquentiel",
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('sous.actions') or '/'
    )
    responsable_realisation = fields.Many2one('hr.employee', string='Responsable de Réalisation')
    delai_realisation = fields.Datetime(string='Délai de Réalisation')
    responsable_suivi = fields.Many2one('hr.employee', string='Responsable de Suivi')
    delai_suivi = fields.Datetime(string='Délai de Suivi')
    gravite = fields.Selection([
        ('faible', 'Faible'),
        ('moyenne', 'Moyenne'),
        ('elevee', 'Élevée')
    ], string='Gravité')
    priorite = fields.Selection([
        ('basse', 'Basse'),
        ('moyenne', 'Moyenne'),
        ('haute', 'Haute')
    ], string='Priorité')
    piece_jointe = fields.Binary(string='Pièce Jointe')
    taux_realisation = fields.Float(string='Taux de Réalisation')
    depenses = fields.Float(string='Dépenses')
    commentaire = fields.Text(string='Commentaire')

    @api.model
    def create(self, vals):
        if not vals.get('numero_sequentiel'):
            vals['numero_sequentiel'] = self.env['ir.sequence'].next_by_code('sous.actions') or '/'
        return super(SousActions, self).create(vals)
