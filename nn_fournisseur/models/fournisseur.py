from odoo import models, fields, api


class Fournisseur(models.Model):
    _name = 'fournisseur.fournisseur'
    _description = 'Fiche Fournisseur'

    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur', ondelete='set null')
    code = fields.Char(string="Code fournisseur", required=True, copy=False, readonly=True, default="New")
    company_name = fields.Char(string='Raison sociale')
    address = fields.Text(string='Adresse')
    phone = fields.Char(string='Numéro de téléphone')
    email = fields.Char(string='Email')
    category_id = fields.Many2one('fournisseur.category', string='Catégorie')
    fournisseur_type = fields.Selection([
        ('materials', 'Matériaux'),
        ('services', 'Services'),
        ('transport', 'Transport')
    ], string='Type de fournisseur')
    is_approved = fields.Boolean(string='Fournisseur agréé')
    attachment = fields.Binary(string='Pièce jointe')
    attachment_name = fields.Char(string="Nom du fichier")
    introduction_date = fields.Date(string="Date d'introduction")
    evaluation_frequency = fields.Selection([
        ('monthly', 'Mensuelle'),
        ('quarterly', 'Trimestrielle'),
        ('annually', 'Annuelle')
    ], string="Périodicité d'évaluation")

    # Relations avec les autres modèles

    evaluation_ids = fields.One2many('evaluation', 'four_id', string='Évaluations')
    claim_ids = fields.One2many('reclamation', 'far_id', string='Réclamations')

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            record = super(Fournisseur, self).create(vals)
            record.code = f"DOC-{record.id:02d}"
            return record
        return super(Fournisseur, self).create(vals)


class FournisseurCategory(models.Model):
    _name = 'fournisseur.category'
    _description = 'Catégorie de fournisseur'

    name = fields.Char(string='Nom', required=True)
    description = fields.Text(string='Description')


