from odoo import models, fields, api, _


class Audit(models.Model):
    _name = "audit.audit"
    _description = 'Audit'

    name = fields.Char(string="Code", required=True, copy=False, readonly=True, default="New")
    demandeur_id = fields.Many2one(
        'hr.employee',
        string='Demandeur de l\'audit',
        required=True,
    )

    state = fields.Selection([
        ('non_realise', 'Non réalisé'),
        ('en_cours', 'En cours'),
        ('realise', 'Réalisé'),
    ], string='État de l\'audit', default='non_realise', tracking=True)

    plan_ids = fields.One2many(
        'audit.plan',
        'audit_id',
        string='Plan d\'audit',
    )

    date_debut_cloture = fields.Datetime(
        string='Date de début de clôture',
        help="Date de début de la clôture de l'audit"
    )
    date_fin_cloture = fields.Datetime(
        string='Date de fin de clôture',
        help="Date de fin de la clôture de l'audit"
    )
    etat_audit = fields.Selection([
        ('non_realise', 'Non réalisé'),
        ('realise', 'Réalisé'),
    ], string='État de l\'audit (clôture)',
        help="Statut de l'audit à la fin de la clôture")


    def action_start(self):

        self.state = 'en_cours'

    def action_done(self):

        self.state = 'realise'


@api.model
def create(self, vals):
    if vals.get('name', 'New') == 'New':
        vals['name'] = self.env['ir.sequence'].next_by_code('audit.name') or _('New')
    return super(Audit, self).create(vals)


class AuditPlan(models.Model):
    _name = 'audit.plan'
    _description = 'Plan d\'audit'

    audit_id = fields.Many2one(
        'audit.audit',
        string='Audit',
        required=True,
        ondelete='cascade'
    )

    # Ajoutez ici les autres champs nécessaires pour votre plan d'audit
    name = fields.Char(string='Description', required=True)
    date_planned = fields.Date(string='Date planifiée')
    responsable_id = fields.Many2one('hr.employee', string='Responsable')
    observations = fields.Text(string='Observations')

