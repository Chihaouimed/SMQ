from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError


class Documentation(models.Model):
    _name = 'documentation'
    _description = 'Gestion de la Documentation'
    _inherit = ['mail.thread']

    name = fields.Char(string="Nom")
    code = fields.Char(string="Code", required=True, copy=False, readonly=True, default="New")
    libelle = fields.Char(string="Libellé", required=True)
    type_documentation = fields.Many2one('type.documentation', string="Type de Documentation",
                                         help="Sélectionnez le type de documentation.")
    file = fields.Binary(string="Fichier PDF", attachment=True)
    file_name = fields.Char(string="Nom du fichier")
    version = fields.Char(string='Version', required=True)
    site = fields.Many2one('site', string="Type du site")
    activite = fields.Many2one('activite', string="Type activité")
    selection_redacteur = fields.Many2one('hr.employee', string="Rédacteur Responsable")
    selection_verificateur = fields.Many2one('res.users', string="Vérificateur Responsable")
    selection_approbateur = fields.Many2one('res.users', string="Approbateur Responsable")
    liste_informee = fields.One2many('document.informed.person', 'document_id', string="Liste des Personnes Informées")
    date_creation = fields.Datetime(string="Date de Création", default=fields.Datetime.now, readonly=True)
    rejected = fields.Boolean(string="Rejeted", default=False)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('verification', 'En Attente de vérification'),
        ('approbation', 'En Attente d’approbation'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('archive', 'Archivé'),
    ], string="État", default='draft')

    partner_id = fields.Many2one('res.partner', string="Client")
    raison_rejet = fields.Text(string="Raison du rejet")

    @api.depends('state')
    def _onchange_email_sent(self):
        for record in self:
            if record.state == 'approved':
                # Vérifie que la liste des informés n'est pas vide
                if not record.liste_informee:
                    raise UserError("Veuillez ajouter au moins une personne informée avant d'approuver.")

                # Parcours chaque personne de la liste et envoie un e-mail
                for person in record.liste_informee:
                    partner = person.partner_id
                    if partner.email:  # Vérifie que l'adresse e-mail existe
                        subject = 'Document Approuvé'
                        body_html = """
                                <p>Bonjour {name},</p>
                                <p>Le document a été approuvé. Merci de prendre connaissance de cette information.</p>
                                <p>Cordialement,</p>
                            """.format(name=partner.name)

                        # Création et envoi de l'e-mail
                        mail_values = {
                            'email_to': partner.email,
                            'subject': subject,
                            'body_html': body_html,
                            'email_from': self.env.user.email or 'noreply@exemple.com',
                            # Adresse par défaut si l'utilisateur n'en a pas
                        }
                        mail = self.env['mail.mail'].create(mail_values)
                        mail.send()

    def action_state_email_sent(self):
        for record in self:
            if record.state == 'approved':
                if not record.liste_informee:
                    raise UserError("Veuillez ajouter au moins une personne informée avant d'approuver.")
                for person in record.liste_informee:
                    email = person.name.work_email
                    if email:
                        subject = 'Document Approuvé'
                        body_html = f"""
                              <p>Bonjour {person.name.name},</p>
                              <p>Le document a été approuvé. Merci de prendre connaissance de cette information.</p>
                              <p>Cordialement,</p>
                          """
                        mail_values = {
                            'email_to': email,
                            'subject': subject,
                            'body_html': body_html,
                            'email_from': self.env.user.email or 'noreply@exemple.com',
                        }
                        self.env['mail.mail'].create(mail_values).send()

    def action_change_state_approved(self):
        self.write({'state': 'approved'})
        self.action_state_email_sent()

    def action_rejeter(self):
        return {
            'type':'ir.actions.act_window',
            'name':'Rejet de la documentation',
            'res_model':'document.rejection.wizard',
            'view_mode':'form',
            'target':'new',
            'context':{
                'default_documentation_id':self.id,
            }


        }

    def action_set_verification(self):
        for rec in self:
            rec.state = 'verification'

    def action_set_approbation(self):
        for rec in self:
            rec.state = 'approbation'

    def action_archive(self):
        for rec in self:
            rec.state = 'archive'

    def action_analyse(self):
        for rec in self:
            rec.state = 'draft'

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            record = super(Documentation, self).create(vals)
            record.code = f"DOC-{record.id:02d}"
            return record
        return super(Documentation, self).create(vals)


class DocumentInformedPerson(models.Model):
    _name = 'document.informed.person'
    _description = 'Personnes informées pour un document'

    name = fields.Many2one('hr.employee', string='Employé')
    mail = fields.Char(related='name.work_email')
    document_id = fields.Many2one('documentation', string="Document lié")


class TypeDocumentation(models.Model):
    _name = 'type.documentation'
    _description = 'Type de Documentation'
    _rec_name = 'name'

    name = fields.Char(string="Nom du Type de Documentation", required=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('verification', 'En Attente de vérification'),
        ('approbation', 'En Attente d’approbation'),
        ('approuve', 'Approuvé'),
        ('rejete', 'Rejeté'),
        ('archive', 'Archivé'),
    ], string="État", default='draft')
    code = fields.Char(string="Code", required=True, copy=False, readonly=True, default="New")
    type_documentation = fields.Many2one('type.documentation', string="Type de Documentation",
                                         help="Sélectionnez le type de documentation.")
    file_name = fields.Char(string="Nom du fichier")


class Site(models.Model):
    _name = 'site'
    _description = 'Site associé'

    name = fields.Char(string="Nom du site", required=True)


class Activite(models.Model):
    _name = 'activite'
    _description = 'Activité associée'

    name = fields.Char(string="Activité associée", required=True)
