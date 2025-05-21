from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

from datetime import datetime


class DocumentClient(models.Model):
    _name = 'document.client'
    _description = 'Document Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_creation desc'

    name = fields.Char(string='Nom du document', required=True, tracking=True)
    reference = fields.Char(string='Référence', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True)
    date_creation = fields.Date(string='Date de création', default=fields.Date.today, tracking=True)
    date_expiration = fields.Date(string='Date d\'expiration', tracking=True)
    type_document = fields.Selection([
        ('contrat', 'Contrat'),
        ('facture', 'Facture'),
        ('devis', 'Devis'),
        ('autre', 'Autre')
    ], string='Type de document', default='autre', required=True, tracking=True)

    description = fields.Text(string='Description')
    note = fields.Html(string='Notes')

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('expire', 'Expiré'),
        ('annule', 'Annulé')
    ], string='État', default='brouillon', required=True, tracking=True)

    active = fields.Boolean(string='Actif', default=True)

    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=lambda self: [('res_model', '=', 'document.client')],
        string='Pièces jointes',
        auto_join=True,
    )

    document_file = fields.Binary(string='Fichier', attachment=True)
    document_filename = fields.Char(string='Nom du fichier')

    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user, tracking=True)
    attachment_count = fields.Integer(string='Nombre de pièces jointes', compute='_compute_attachment_count')

    # Méthode pour calculer le nombre de pièces jointes
    def _compute_attachment_count(self):
        for record in self:
            attachment_ids = self.env['ir.attachment'].search([
                ('res_model', '=', 'document.client'),
                ('res_id', '=', record.id)
            ])
            record.attachment_count = len(attachment_ids)

    # Méthode pour ouvrir la vue des pièces jointes
    def action_view_attachments(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError("Veuillez renseigner le client.")
        else:
            return {

                'name': _('Pièces jointes'),
                'domain': [('res_model', '=', 'document.client'), ('res_id', '=', self.id)],
                'res_model': 'ir.attachment',
                'type': 'ir.actions.act_window',
                'view_mode': 'kanban,tree,form',
                'context': {
                    'default_res_model': 'document.client',
                    'default_res_id': self.id,
                },
                'help': """
                   <p class="o_view_nocontent_smiling_face">
                       Ajoutez des pièces jointes à ce document
                   </p>
               """,
            }

        # Méthode pour télécharger rapidement une nouvelle pièce jointe

    def action_upload_attachment(self):
        self.ensure_one()
        return {
            'name': _('Ajouter une pièce jointe'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ir.attachment',
            'view_id': False,
            'target': 'new',
            'context': {
                'default_res_model': 'document.client',
                'default_res_id': self.id,
            },
        }

        # Calcul du statut en fonction de la date d'expiration

    @api.depends('date_expiration')
    def _compute_status(self):
        today = fields.Date.today()
        for record in self:
            if record.date_expiration and record.date_expiration < today:
                record.status = 'expired'
            else:
                record.status = 'valid'

    status = fields.Selection([
        ('valid', 'Valide'),
        ('expired', 'Expiré')
    ], string='Statut', compute='_compute_status', store=True)

    # Contrainte pour vérifier que la date d'expiration est supérieure à la date de création
    @api.constrains('date_creation', 'date_expiration')
    def _check_dates(self):
        for record in self:
            if record.date_expiration and record.date_creation and record.date_expiration < record.date_creation:
                raise ValidationError(_("La date d'expiration doit être ultérieure à la date de création!"))

    # Méthode pour changer l'état du document
    def action_validate(self):
        self.write({'state': 'valide'})

    def action_cancel(self):
        self.write({'state': 'annule'})

    def action_draft(self):
        self.write({'state': 'brouillon'})
