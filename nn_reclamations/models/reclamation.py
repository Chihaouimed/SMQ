from odoo import models, fields, api
from odoo.exceptions import UserError


class Reclamation(models.Model):
    _name = 'reclamation'
    _description = 'Réclamation Fournisseur'

    name = fields.Char(string="Code", required=True, copy=False, readonly=True, default="New")
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur')
    far_id = fields.Char(related='fournisseur_id.name',string='Fournisseur')
    date_reclamation = fields.Date(string='Date de la Réclamation', required=True)
    description = fields.Text(string='Description', required=True)
    type_reclamation = fields.Many2one('type.reclamation', string="Type de réclamation")
    gravite = fields.Selection([
        ('low', 'Faible'),
        ('medium', 'Moyenne'),
        ('high', 'Élevée'),
    ], string='Gravité', required=True)
    designation = fields.Char(string='Désignation', required=True)
    attachment = fields.Binary(string='Pièce Jointe')
    attachment_name = fields.Char(string='Nom de la Pièce Jointe')
    actions = fields.Text(string='Actions à Prendre')
    decision = fields.Char(string='Décisions prises')
    plan_action_declenche = fields.Boolean(
        string="Plan d'action déclenché"

    )
    plan_action_joint = fields.Binary(string="Plan d'action joint")
    plan_action_filename = fields.Char(string="Nom du fichier")
    cout_reclamation = fields.Float(string="Coût de la réclamation")
    feedback_client = fields.Selection([
        ('satisfait', 'Satisfait'),
        ('insatisfait', 'Insatisfait'),
        ('neutre', 'Neutre'),
    ], string="Feedback client", default=False)
    state = fields.Selection([
        ('draft', 'Nouvelle'),
        ('prise_en_charge', 'Prise en charge'),
        ('en_cours', 'En cours de traitement'),
        ('analyse', 'Analyse'),
        ('traitee', 'Traitée'),
        ('cloturee', 'Clôturée'),
        ('annule', 'Annulée'),
    ], string="État", default='draft')

    date_cloture = fields.Datetime(string='Date de clôture', default=fields.Datetime.now, readonly=True)
    responsable_traitement_id = fields.Many2one(
        'hr.employee',
        string="Responsable de traitement"
    )
    suivi_ids = fields.One2many('reclamation.suivi', 'reclamation_id', string="Suivi")

    ################################date de cloture quand le state est cloture#######################

    # Définition d'une méthode pour calculer si le bouton Clôturer doit être visible
    can_cloturer = fields.Boolean(compute='_compute_can_cloturer', store=False)

    @api.depends('state')
    def compute_can_cloturer(self):
        for record in self:
            # Le bouton "Clôturer" doit être visible si l'état est "en_cours"
            record.can_cloturer = record.state == 'en_cours'

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            # Crée l'enregistrement normalement
            record = super(Reclamation, self).create(vals)
            # Attribue un code unique basé sur l'ID de l'enregistrement
            record.name = f"DOC-{record.id:02d}"
            return record
        return super(Reclamation, self).create(vals)

    def action_generer_fnc(self):
        for rec in self:
            fnc = self.env['non.conformite'].search([('reclamation_id', '=', rec.id)], limit=1)

            if fnc:
                if fnc.state != 'draft':
                    raise UserError(
                        "Une non-conformité est déjà générée pour cette réclamation et son état n'est pas 'Brouillon'.")
                else:
                    fnc.write({
                        'description': rec.description,
                        'state': 'draft',
                    })
                    rec.plan_action_declenche = True

                    # Affiche un message de succès après mise à jour
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Succès',
                            'message': 'La non-conformité existante a été mise à jour avec succès.',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
            else:
                self.env['non.conformite'].create({
                    'description': rec.description,
                    'reclamation_id': rec.id,
                    'state': 'draft',
                })
                rec.plan_action_declenche = True

                # Affiche un message de succès après création
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Succès',
                        'message': 'La non-conformité a été créée avec succès.',
                        'type': 'success',
                        'sticky': False,
                    }
                }

    # State changing buttons ========================
    def action_analyse(self):
        for rec in self:
            rec.state = 'analyse'

    def action_traiter(self):
        for rec in self:
            rec.state = 'traitee'

    def action_prise_en_charge(self):
        for rec in self:
            rec.state = 'prise_en_charge'

    def action_en_cours(self):
        for rec in self:
            rec.state = 'en_cours'

    def action_annule(self):
        for rec in self:
            rec.state = 'annule'

    def action_remettre_brouillon(self):
        for rec in self:
            rec.state = 'draft'

    def action_cloturer(self):
        for record in self:
            record.state = 'cloturee'
    # ===============================================================================


class TypeReclamation(models.Model):
    _name = 'type.reclamation'
    _description = 'Type de Réclamation'

    name = fields.Char(string="Nom", required=True)


class ReclamationSuivi(models.Model):
    _name = 'reclamation.suivi'
    _description = "Suivi de Réclamation"

    reclamation_id = fields.Many2one('reclamation', string="Réclamation", ondelete='cascade')
    responsable_suivi = fields.Many2one('hr.employee', string="Responsable de suivi")
    delai_fixe = fields.Date(string="Délai fixé")
    rapport_suivi = fields.Text(string="Rapport de suivi")
    date_cloture = fields.Datetime(string="Date de clôture", related='reclamation_id.date_cloture', store=True)
