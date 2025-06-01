from odoo import api, fields, models, _


class SMQReportingNonConformity(models.Model):
    _name = 'smq.reporting.nonconformity'
    _description = 'Reporting Non-conformité et Réunion SMQ'
    _auto = False  # <- très important pour dire à Odoo que c’est une vue SQL

    type = fields.Selection([
        ('reunion', 'Réunion'),
        ('nonconformity', 'Non-conformité')
    ], string="Type")

    reunion_id = fields.Many2one('reunion.reunion', string='Réunion')
    reunion_type = fields.Selection([
        ('equipe', 'Réunion d\'équipe'),
        ('client', 'Réunion client'),
        ('projet', 'Réunion de projet'),
        ('departement', 'Réunion de département'),
        ('autre', 'Autre')
    ], string='Type de réunion')
    reunion_state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('confirme', 'Confirmée'),
        ('annule', 'Annulée'),
        ('termine', 'Terminée')
    ], string='État de la réunion')

    nonconformity_id = fields.Many2one('smq.nonconformity', string='Non-conformité')
    process_id = fields.Many2one('smq.process', string='Processus')
    nonconformity_status = fields.Selection([
        ('open', 'Ouverte'),
        ('in_progress', 'En cours'),
        ('closed', 'Clôturée')
    ], string='Statut')

    responsible_id = fields.Many2one('res.users', string='Responsable')
    demandeur_id = fields.Many2one('hr.employee', string='Demandeur')
    date = fields.Date(string="Date")

    source_non_conformite = fields.Selection([
        ('interne', 'Interne'),
        ('client', 'Client'),
        ('fournisseur', 'Fournisseur'),
        ('audit', 'Audit')
    ], string="Source de non conformité")

    count = fields.Integer(string='Nombre')
    year = fields.Char(string='Année')
    month = fields.Char(string='Mois')
    quarter = fields.Char(string='Trimestre')
    produit_non_conforme_id = fields.Many2one(
        'product.product',
        string="Produit non conforme"
    )

    type_reclamation = fields.Many2one('type.reclamation', string="Type de réclamation")
    product_category_id = fields.Many2one('product.category', string='Type de produit')
    site = fields.Char(string="Site Concerné")
