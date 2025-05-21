from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ComplianceType(models.Model):
    _name = 'compliance.type'
    _description = 'Type de fiche de conformité'

    name = fields.Char('Nom du type', required=True)
    description = fields.Text('Description')
    active = fields.Boolean('Actif', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Le nom du type doit être unique !"),
    ]


class ComplianceSheet(models.Model):
    _name = 'compliance.sheet'
    _description = 'Fiche de conformité'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Référence', readonly=True, copy=False, default='Nouveau')
    compliance_type_id = fields.Many2one('compliance.type', string='Type de fiche', required=True, tracking=True)
    source = fields.Char('Source de la liste', tracking=True)
    regulation_name = fields.Char('Nom de la réglementation', required=True, tracking=True)
    is_applicable = fields.Boolean('Applicable', default=True, tracking=True)
    action_plan = fields.Text('Plan d\'action', tracking=True)
    create_date = fields.Datetime('Date de création', readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Pièces jointes')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('compliant', 'Conforme'),
        ('non_compliant', 'Non conforme'),
    ], string='État', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('compliance.sheet') or 'Nouveau'
        return super(ComplianceSheet, self).create(vals_list)

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_set_compliant(self):
        self.write({'state': 'compliant'})

    def action_set_non_compliant(self):
        self.write({'state': 'non_compliant'})

    # Séquence pour les références des fiches intégrée dans le code au lieu d'un fichier XML séparé
    @api.model
    def _init_sequence(self):
        """ Initialiser la séquence pour les fiches de conformité """
        seq_vals = {
            'name': 'Fiches de conformité',
            'code': 'compliance.sheet',
            'prefix': 'CONF/%(year)s/',
            'padding': 5,
            'company_id': False,
        }
        if not self.env['ir.sequence'].search([('code', '=', seq_vals['code'])]):
            self.env['ir.sequence'].create(seq_vals)

    # Création des types par défaut
    @api.model
    def _init_compliance_types(self):
        """ Initialiser les types de conformité par défaut """
        default_types = [
            ('Juridique', 'Réglementations juridiques et légales'),
            ('Fiscal', 'Obligations fiscales et comptables'),
            ('Sécurité', 'Normes de sécurité et de prévention'),
            ('Environnement', 'Réglementations environnementales'),
            ('Qualité', 'Normes et certifications qualité'),
            ('RH', 'Réglementations liées aux ressources humaines'),
            ('IT', 'Conformité informatique et protection des données'),
        ]

        for name, description in default_types:
            if not self.env['compliance.type'].search([('name', '=', name)]):
                self.env['compliance.type'].create({
                    'name': name,
                    'description': description,
                })

    # Post-installation hook
    @api.model
    def _post_init_hook(self):
        self._init_sequence()
        self._init_compliance_types()