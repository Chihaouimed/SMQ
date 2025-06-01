# nn_evaluation/models/evaluation.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Evaluation(models.Model):
    _name = 'evaluation'
    _description = 'Évaluation'
    _rec_name = 'fournisseur_id'  # Pour l'affichage dans les relations
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Fournisseur à évaluer
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur', required=True)
    four_id = fields.Char(related='fournisseur_id.name')

    # Type de produit
    product_category_id = fields.Many2one('product.category', string='Type de produit')

    # Critères d'évaluation
    evaluation_criteria_ids = fields.One2many('evaluation.criteria', 'evaluation_id', string='Critères d\'évaluation')

    # Score total calculé
    total_score = fields.Float(string='Score Total', compute='_compute_total_score', store=True)

    # Périodicité d'évaluation
    periodicity = fields.Selection([
        ('monthly', 'Mensuelle'),
        ('quarterly', 'Trimestrielle'),
        ('annual', 'Annuelle'),
    ], string='Périodicité d\'évaluation', default='monthly')

    # Actions associées
    action_ids = fields.Many2many('action.request', string='Actions associées')

    # État de l'évaluation
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('validated', 'Validé'),
    ], string='État de l\'évaluation', default='draft')

    # Date d'évaluation - CORRECTION de la syntaxe
    evaluation_date = fields.Date(string='Date d\'évaluation', default=lambda self: fields.Date.today())
    ai_analysis_ids = fields.One2many(
        'supplier.ai.analysis',
        'evaluation_id',  # Champ inverse dans supplier.ai.analysis
        string='Analyses IA'
    )

    ai_analysis_count = fields.Integer(
        string='Nombre d\'analyses IA',
        compute='_compute_ai_analysis_count'
    )

    def action_view_evaluation_result(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Résultat - {self.fournisseur_id.name}',
            'res_model': 'evaluation',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('nn_evaluation.view_evaluation_real_result_form').id,
            # Remplacez nn_evaluation par votre nom de module
            'target': 'current',
        }

    @api.depends('ai_analysis_ids')
    def _compute_ai_analysis_count(self):
        for record in self:
            record.ai_analysis_count = len(record.ai_analysis_ids)

    def action_generate_ai_insights(self):
        """Génère une nouvelle analyse IA"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle Analyse IA',
            'res_model': 'supplier.ai.analysis',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_evaluation_id': self.id,
                'default_fournisseur_id': self.fournisseur_id.id,
            }
        }

    def action_view_ai_analyses(self):
        """Voir toutes les analyses IA"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Analyses IA',
            'res_model': 'supplier.ai.analysis',
            'view_mode': 'tree,form',
            'domain': [('evaluation_id', '=', self.id)],
        }

    @api.depends('evaluation_criteria_ids.score')
    def _compute_total_score(self):
        """Calcule le score total de l'évaluation"""
        for record in self:
            if record.evaluation_criteria_ids:
                total = sum(criteria.score for criteria in record.evaluation_criteria_ids)
                count = len(record.evaluation_criteria_ids)
                record.total_score = total / count if count > 0 else 0.0
            else:
                record.total_score = 0.0

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
    _description = 'Critères d\'évaluation'
    _rec_name = 'name'

    evaluation_id = fields.Many2one('evaluation', string='Évaluation liée', required=True, ondelete='cascade')
    name = fields.Char(string='Critère', required=True)
    score = fields.Float(string='Note', required=True, default=0.0)
    max_score = fields.Float(string='Note maximale', default=10.0)
    weight = fields.Float(string='Poids (%)', default=1.0)
    comment = fields.Text(string='Commentaire')

    @api.constrains('score', 'max_score')
    def _check_score_range(self):
        for record in self:
            if record.score < 0 or record.score > record.max_score:
                raise ValidationError(f"Le score doit être entre 0 et {record.max_score}")


class ProductCategory(models.Model):
    _inherit = 'product.category'

    # Exemple de champ supplémentaire
    category_description = fields.Text(string='Description de la catégorie')


class ActionRequest(models.Model):
    _name = 'action.request'
    _description = 'Demande d\'action'
    _rec_name = 'name'

    name = fields.Char(string='Nom de l\'action', required=True)
    description = fields.Text(string='Description')
    responsible_id = fields.Many2one('res.users', string='Responsable')
    deadline = fields.Date(string='Date limite')
    priority = fields.Selection([
        ('low', 'Faible'),
        ('medium', 'Moyenne'),
        ('high', 'Élevée'),
        ('urgent', 'Urgente')
    ], string='Priorité', default='medium')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft')
