from odoo import models, fields


class Evaluation(models.Model):
    _name = 'evaluation'
    _description = 'Évaluation'

    # Fournisseur à évaluer
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur')
    four_id = fields.Many2one('fournisseur.fournisseur', string='Fournisseur', related='fournisseur_id')

    # Type de produit
    product_category_id = fields.Many2one('product.category', string='Type de produit')

    # Critères d’évaluation
    evaluation_criteria_ids = fields.One2many('evaluation.criteria', 'evaluation_id', string='Critères d’évaluation')

    # Périodicité d’évaluation
    periodicity = fields.Selection([
        ('monthly', 'Mensuelle'),
        ('quarterly', 'Trimestrielle'),
        ('annual', 'Annuelle'),
    ], string='Périodicité d’évaluation', default='monthly')

    # Actions associées
    action_ids = fields.Many2many('action.request', string='Actions associées')

    # État de l’évaluation
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('validated', 'Validé'),
    ], string='État de l’évaluation', default='draft')

    def action_pending(self):
        for rec in self:
            rec.state = 'pending'

    def action_validate(self):
        for rec in self:
            rec.state = 'validated'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'


class EvaluationCriteria(models.Model):
    _name = 'evaluation.criteria'
    _description = 'Critères d’évaluation'

    evaluation_id = fields.Many2one('evaluation', string='Évaluation liée')
    name = fields.Char(string='Critère', required=True)
    score = fields.Float(string='Note', required=True, default=0.0)
    comment = fields.Text(string='Commentaire')


class ProductCategory(models.Model):
    _inherit = 'product.category'

    # Exemple de champ supplémentaire
    category_description = fields.Text(string='Description de la catégorie')


class ActionRequest(models.Model):
    _name = 'action.request'
    _description = 'Demande d\'action'

    name = fields.Char(string='Nom de l\'action', required=True)
    description = fields.Text(string='Description')
