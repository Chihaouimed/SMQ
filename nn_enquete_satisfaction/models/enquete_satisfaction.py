from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class EnqueteSatisfaction(models.Model):
    _name = 'enquete.satisfaction'
    _description = 'Enquête de Satisfaction Client'
    _order = 'date_debut desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Pour ajouter le chatter et les activités

    reference = fields.Char(string="Référence", required=True, copy=False, readonly=True, default="New")
    name = fields.Char(string="Référence de l'enquête", required=True, copy=False, readonly=True, default='New')
    date_debut = fields.Date(string="Date de début", default=fields.Date.context_today, tracking=True)
    date_fin = fields.Date(string="Date de fin", tracking=True)
    client_ids = fields.Many2many('res.partner', string="Clients concernés")
    survey_id = fields.Many2one('survey.survey', string="Sondage", help="Associer un sondage à cette enquête.",
                                tracking=True)
    survey_url = fields.Char(string="URL du sondage", compute="_compute_survey_url")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('cloturee', 'Clôturée')
    ], string="État", default='draft', tracking=True)
    responsible_id = fields.Many2one('res.users', string="Responsable", tracking=True)
    closure_deadline = fields.Date(string="Date limite de clôture")
    action_effectiveness = fields.Selection([
        ('faible', 'Faible'),
        ('moyenne', 'Moyenne'),
        ('elevee', 'Élevée')
    ], string="Efficacité des actions")
    closure_attachment = fields.Binary(string="Pièce jointe de clôture")
    closure_comment = fields.Text(string="Commentaire de clôture")

    type_questionnaire = fields.Selection([
        ('court', 'Court'),
        ('detaille', 'Détaillé'),
        ('custom', 'Personnalisé')
    ], string="Type de questionnaire", required=True)

    # Calcul de l'URL du sondage
    @api.depends('survey_id')
    def _compute_survey_url(self):
        for record in self:
            if record.survey_id:
                record.survey_url = f'/survey/start/{record.survey_id.access_token}'
            else:
                record.survey_url = False

    # Méthode pour assigner un responsable
    def action_assign_responsible(self):
        self.ensure_one()
        self.write({
            'responsible_id': self.env.user.id
        })
        self.message_post(
            body=f"Le responsable a été défini comme {self.env.user.name}",
            message_type='notification'
        )
        return True

    # Méthode améliorée d'envoi des emails avec lien vers le sondage
    def action_send_emails(self):
        self.ensure_one()
        if not self.client_ids:
            raise UserError("Veuillez ajouter au moins un client avant d'envoyer l'enquête.")

        if not self.survey_id:
            raise UserError("Veuillez sélectionner un sondage avant d'envoyer l'enquête.")

        # Passer à l'état "En cours" lors de l'envoi
        self.write({'state': 'en_cours'})

        # Créer les invitations pour chaque client
        SurveyUserInput = self.env['survey.user_input']
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        for client in self.client_ids:
            if client.email:
                # Créer une participation pour ce client
                user_input = SurveyUserInput.create({
                    'survey_id': self.survey_id.id,
                    'partner_id': client.id,
                    'email': client.email,
                    'deadline': self.date_fin,
                })

                # Construire l'URL publique avec le token d'accès
                survey_url = f"{base_url}/survey/start/{self.survey_id.id}?token={user_input.access_token}"

                # Préparer le mail avec le lien vers le sondage
                template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)
                if template:
                    # Utiliser le template existant d'Odoo Survey
                    email_values = {
                        'email_to': client.email,
                        'subject': f"Enquête de Satisfaction: {self.reference}",
                    }
                    template.with_context(
                        survey_url=survey_url,
                        survey_name=self.survey_id.title,
                        deadline=self.date_fin
                    ).send_mail(user_input.id, email_values=email_values)
                else:
                    # Créer un email personnalisé si le template n'est pas trouvé
                    body_html = f"""
                        <p>Bonjour {client.name},</p>
                        <p>Nous vous invitons à répondre à notre enquête de satisfaction concernant {self.reference}.</p>
                        <p>Cliquez sur ce lien pour accéder au sondage : <a href="{survey_url}">{self.survey_id.title}</a></p>
                        <p>Cordialement,</p>
                    """
                    mail_values = {
                        'email_to': client.email,
                        'subject': f"Enquête de Satisfaction: {self.reference}",
                        'body_html': body_html,
                        'email_from': self.env.user.email or self.env.company.email,
                    }
                    mail = self.env['mail.mail'].create(mail_values)
                    mail.send()

        self.message_post(body="Enquête envoyée à tous les clients sélectionnés.", message_type='notification')
        return True

    # Méthode pour clôturer l'enquête
    def action_close_survey(self):
        self.ensure_one()
        if not self.responsible_id:
            raise UserError("Veuillez assigner un responsable avant de clôturer l'enquête.")

        self.write({'state': 'cloturee'})
        self.message_post(body="Enquête clôturée.", message_type='notification')
        return True

    # Méthode pour marquer l'enquête comme terminée
    def action_mark_as_completed(self):
        self.ensure_one()
        self.write({'state': 'terminee'})
        self.message_post(body="Enquête marquée comme terminée.", message_type='notification')
        return True

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('enquete.satisfaction') or 'New'
        if vals.get('name', 'New') == 'New':
            vals['name'] = vals.get('reference', 'New')
        return super(EnqueteSatisfaction, self).create(vals)
