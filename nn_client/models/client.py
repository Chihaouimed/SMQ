from odoo import models, fields, api, _


class Client(models.Model):
    _inherit = "res.partner"

    raison_sociale = fields.Char(string="Raison Sociale")
    code = fields.Char(string="Code", required=True, copy=False, readonly=True, default="New")
    activite = fields.Many2one(
        'activite',
        string="Type d'activité",
        help="Sélectionnez le type d'activité associée."
    )
    type_client = fields.Many2one(
        'type.client',
        string="Type de client",
        help="Sélectionnez le type de client."
    )
    categorie = fields.Many2one(
        'categorie',
        string="Catégorie",
        help="Sélectionnez la catégorie."
    )
    company_type = fields.Selection(
        string='Company Type',
        selection=[
            ('person', 'Individual'),
            ('company', 'Company'),
            ('client', 'Client')

        ],
        default='client',  # Valeur par défaut
        compute='_compute_company_type',
        inverse='_write_company_type'
    )
    document_count = fields.Integer(
        string="Nombre de Documents",
        compute="_compute_document_count"
    )
    document_client_ids = fields.One2many('document.client', 'partner_id', string='Documents Clients')
    date = fields.Datetime(string="Date d introduction", default=fields.Datetime.now, readonly=True)

    def _compute_document_count(self):
        for record in self:
            record.document_count = self.env['documentation'].search_count([('partner_id', '=', record.id)])

    def action_view_documents(self):
        """Affiche les documents liés au client"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents liés',
            'res_model': 'documentation',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],  # Filtrer les documents liés au client
            'context': {'default_partner_id': self.id},  # Pré-remplir le champ client
        }

    ##############piece jointes#########################################
    attachment_count = fields.Integer(string="Nombre de pièces jointes", compute='_compute_attachment_count')

    def action_view_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pièces jointes',
            'res_model': 'ir.attachment',
            'domain': [('res_model', '=', 'res.partner'), ('res_id', '=', self.id)],
            'view_mode': 'kanban,tree,form',
            'target': 'current',
            'context': {
                'default_res_model': 'res.partner',
                'default_res_id': self.id,
            },
        }

    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', rec.id)
            ])

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('client.code') or _('New')
        return super(Client, self).create(vals)


class Activite(models.Model):
    _name = 'activite'
    _description = 'Activité associée'

    name = fields.Char(string="Activité associée", required=True)


class TypeClient(models.Model):
    _name = 'type.client'
    _description = 'Type de Client'

    name = fields.Char(string="Type de Client", required=True)


class Categorie(models.Model):
    _name = 'categorie'
    _description = 'categorie'

    name = fields.Char(string="Catégorie", required=True)
