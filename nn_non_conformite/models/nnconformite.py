from odoo import models, fields, api
import pandas as pd



class NonConformite(models.Model):
    _name = 'non.conformite'
    _description = 'Fiche Non-Conformité'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Ajoutez cette ligne

    name = fields.Char(string="Code", required=True, copy=False, readonly=True, default="New")
    description = fields.Text(string="Description")
    reclamation_id = fields.Many2one('reclamation', string="Réclamation liée")
    date_detection = fields.Date(string="Date de détection")
    designation_produit = fields.Char(
        string="Désignation du produit non conforme",
    )
    produit_non_conforme_id = fields.Many2one(
        'product.product',
        string="Produit non conforme"
    )
    personnes_a_notifier_ids = fields.Many2many(
        'res.partner',
        string="Personnes à notifier"
    )
    type_non_conformite = fields.Selection(
        string="Type de non-conformité",
        selection=[
            ('qualite', 'Qualité'),
            ('securite', 'Sécurité'),
            ('reglementaire', 'Réglementaire'),
            ('autre', 'Autre')
        ],
    )

    source_non_conformite = fields.Selection([
        ('interne', 'Interne'),
        ('client', 'Client'),
        ('fournisseur', 'Fournisseur'),
        ('audit', 'Audit')
    ], string="Source de non-conformité")


    niveau_gravite = fields.Selection(
        string="Niveau de gravité",
        selection=[
            ('mineure', 'Mineure'),
            ('majeure', 'Majeure'),
            ('critique', 'Critique')
        ],
    )

    piece_jointe = fields.Binary(string="Pièce jointe")
    # NOUVEAUX CHAMPS POUR LA VALIDATION
    numero_of = fields.Char(string="Numéro d'Ordre de Fabrication")
    numero_o = fields.Char(string="Numéro d'Ordre")
    produit_non_conforme_detecte = fields.Boolean(string="Produit non conforme détecté")
    # NOUVEAUX CHAMPS POUR LE TRAITEMENT
    date_traitement = fields.Date(string="Date de traitement")
    cout_non_conformite = fields.Float(string="Coût de non-conformité (en DT)")
    quantite_rejetee = fields.Float(string="Quantité rejetée")
    valeur_quantite_rejetee = fields.Float(string="Valeur de la quantité rejetée")
    quantite_declassee = fields.Float(string="Quantité déclassée")
    valeur_quantite_declassee = fields.Float(string="Valeur de la quantité déclassée")
    quantite_acceptee = fields.Float(string="Quantité acceptée")
    traitement_produit_non_conforme = fields.Selection(
        string="Traitement produit non conforme",
        selection=[
            ('cloture', 'Clôturé'),
            ('non_cloture', 'Non clôturé')
        ]
    )
    date_cloture = fields.Datetime(string="Date de clôture")
    rapport_cloture = fields.Text(string="Rapport de clôture")
    statut_suivi = fields.Selection(
        string="Statut du suivi",
        selection=[
            ('cloture', 'Clôturé'),
            ('non_cloture', 'Non clôturé')
        ]
    )
    actions_correctives_ids = fields.Many2many(
        'actions.correctives',
        string="Actions correctives et préventives"
    )

    date_cloture_suivi = fields.Datetime(string="Date de clôture (suivi)")
    rapport_cloture_suivi = fields.Text(string="Rapport de clôture (suivi)")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('analyse', 'Analyse'),
        ('prise_en_charge', 'Prise en charge'),
        ('en_cours', 'En Cours'),
        ('cloturee', 'Clôturée'),
        ('annule', 'Annulée'),
    ], string='État', default='draft', readonly=True, tracking=True)
    piece_jointe_filename = fields.Char(string="Nom du fichier joint")
    gravite = fields.Selection([
        ('low', 'Faible'),
        ('medium', 'Moyenne'),
        ('high', 'Haute')
    ], string="Gravité", required=True)
    source = fields.Char(string="Source de la Non-Conformité")


    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('non.conformite')
        return super(NonConformite, self).create(vals)

    def action_analyse(self):
        """Mettre l'état à 'Analyse'"""
        for record in self:
            record.state = 'analyse'

    def action_prise_en_charge(self):
        """Mettre l'état à 'Prise en charge'"""
        for record in self:
            record.state = 'prise_en_charge'

    def action_en_cours(self):
        """Mettre l'état à 'En cours'"""
        for record in self:
            record.state = 'en_cours'

    def action_cloturee(self):
        """Mettre l'état à 'Clôturée'"""
        for record in self:
            record.state = 'cloturee'

    def action_annule(self):
        """Mettre l'état à 'Annulée'"""
        for record in self:
            record.state = 'annule'

    def action_remettre_brouillon(self):
        """Remettre l'état à 'Brouillon'"""
        for record in self:
            record.state = 'draft'

    def export_data(self):
        # Récupérer les données de non-conformité
        non_conformites = self.env['non.conformite'].search([])

        # Préparer les données pour l'export
        data = []
        for nc in non_conformites:
            for action in nc.actions_correctives_ids:
                data.append({
                    'description': nc.description,
                    'gravite': nc.gravite,
                    'source': nc.source,
                    'action': action.name,
                    'responsable': action.responsable_id.name,
                    'statut': action.statut
                })

        # Convertir en DataFrame pandas et exporter en CSV
        import pandas as pd
        df = pd.DataFrame(data)
        df.to_csv("C:/Users/bejao/Desktop/exported_data.csv", index=False)
        return True


class ActionsCorrectives(models.Model):
    _name = 'actions.correctives'
    _description = 'Actions Correctives et Préventives'

    name = fields.Char(string="Titre de l'action", required=True)
    description = fields.Text(string="Description")
    date_planifiee = fields.Date(string="Date planifiée")
    responsable_id = fields.Many2one('res.users', string="Responsable")
    statut = fields.Selection([
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée')
    ], string="Statut", default='planifiee')
