from odoo import models, fields, api
from datetime import date, timedelta, datetime
from odoo.exceptions import ValidationError, UserError


class Action(models.Model):
    _name = 'action'
    _description = 'Gestion action'

    name = fields.Char(string="Nom")
    # 1. Numéro séquentiel
    numero_sequentiel = fields.Char(
        string="Numéro Séquentiel",
        readonly=True,
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('action.model') or '/'
    )

    # 2. Désignation
    designation = fields.Char(string="Désignation", required=True)

    # 3. Description
    description = fields.Text(string="Description")

    # 4. Type d'action
    type_action = fields.Selection(
        [
            ('prevention', 'Prévention'),
            ('correction', 'Correction'),
            ('amelioration', 'Amélioration')
        ],
        string="Type d'Action",
        required=True
    )

    # 5. Source d'action
    source_action = fields.Char(string="Source de l'Action", required=True)

    # 6. Cause de l'action
    cause_action = fields.Text(string="Cause de l'Action")

    # 7. Gravité de l'action
    gravite_action = fields.Selection(
        [
            ('faible', 'Faible'),
            ('moyenne', 'Moyenne'),
            ('elevee', 'Élevée')
        ],
        string="Gravité de l'Action",
        required=True
    )

    # 8. Priorité de l'action
    priorite_action = fields.Selection(
        [
            ('basse', 'Basse'),
            ('moyenne', 'Moyenne'),
            ('haute', 'Haute'),
            ('urgente', 'Urgente')
        ],
        string="Priorité de l'Action",
        required=True
    )

    # 9. Responsable de validation de la demande d'action
    responsable_validation = fields.Many2one(
        'hr.employee',
        string="Responsable de Validation",
        required=True
    )

    # 10. Site
    site = fields.Char(string="Site Concerné")

    # Champs pour les sous-actions
    responsable_realisation = fields.Many2one('hr.employee', string='Responsable de Réalisation')
    delai_realisation = fields.Datetime(string='Délai de Réalisation')
    responsable_suivi = fields.Many2one('hr.employee', string='Responsable de Suivi')
    delai_suivi = fields.Datetime(string='Délai de Suivi')
    gravite = fields.Selection([
        ('faible', 'Faible'),
        ('moyenne', 'Moyenne'),
        ('elevee', 'Élevée')
    ], string='Gravité')
    priorite = fields.Selection([
        ('basse', 'Basse'),
        ('moyenne', 'Moyenne'),
        ('haute', 'Haute')
    ], string='Priorité')
    piece_jointe = fields.Binary(string='Pièce Jointe')
    taux_realisation = fields.Float(string='Taux de Réalisation')
    depenses = fields.Float(string='Dépenses (en dt)')
    commentaire = fields.Text(string='Commentaire')

    sous_action_ids = fields.One2many('sous.actions', 'act_id', string='Sous Actions')

    # Champs pour la clôture de l'action
    responsible_id = fields.Many2one(
        'hr.employee', string="Responsable de clôture",
        help="Employé en charge de la clôture de l'action."
    )
    closure_deadline = fields.Datetime(
        string="Délai de clôture",
        help="Date limite pour la clôture de l'action."
    )
    action_effectiveness = fields.Selection(
        [('inefficace', 'Inefficace'),
         ('partiellement_efficace', 'Partiellement efficace'),
         ('efficace', 'Efficace')],
        string="Efficacité de l'action",
        help="Niveau d'efficacité de l'action."
    )
    closure_attachment = fields.Binary(
        string="Pièce jointe (clôture)",
        help="Fichiers joints pour la clôture de l'action (optionnel)."
    )
    closure_comment = fields.Text(
        string="Commentaire (clôture)",
        help="Remarques finales sur la clôture."
    )

    # État de la demande d'action
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('bloque', 'Bloqué'),
        ('termine', 'Terminé'),
        ('cancel', 'Annulé')
    ], string="Statut", default='draft')

    date_cloture = fields.Datetime(string="Date de Clôture", readonly=True)

    # Alerte pour responsables
    alert_responsible = fields.Boolean(string="Alerte activée", default=False)

    # Traçabilité des modifications
    modification_history_ids = fields.One2many('action.corrective.history', 'record_id',
                                               string="Historique des Modifications")

    # Champs pour les personnes concernées
    personnes_concernees_ids = fields.Many2many('res.partner', string="Personnes concernées",
                                                help="Personnes à notifier en cas de changement d'état")
    validation_responsible_id = fields.Many2one('res.users', string="Responsable de validation")
    closure_responsible_id = fields.Many2one('res.users', string="Responsable de clôture")
    fiche_risque_id = fields.Many2one('fiche.risque', string='Fiche de risque associée')

    # Méthode pour assigner le responsable de validation
    def action_assign_validation_responsible(self):
        self.ensure_one()
        self.write({
            'validation_responsible_id': self.env.user.id
        })
        self.message_post(
            body=f"Le responsable de validation a été défini comme {self.env.user.name}",
            message_type='notification'
        )
        return True

    def action_assign_closure_responsible(self):
        self.ensure_one()
        self.write({
            'closure_responsible_id': self.env.user.id
        })
        self.message_post(
            body=f"Le responsable de clôture a été défini comme {self.env.user.name}",
            message_type='notification'
        )
        return True

    def _send_state_change_notifications(self):
        for record in self:
            recipients = []

            # Ajouter les responsables aux destinataires
            if record.responsible_id and record.responsible_id.partner_id:
                recipients.append(record.responsible_id.partner_id.id)

            if record.validation_responsible_id and record.validation_responsible_id.partner_id:
                recipients.append(record.validation_responsible_id.partner_id.id)

            if record.closure_responsible_id and record.closure_responsible_id.partner_id:
                recipients.append(record.closure_responsible_id.partner_id.id)

            # Ajouter les personnes concernées
            if record.personnes_concernees_ids:
                recipients.extend(record.personnes_concernees_ids.ids)

            if recipients:
                subject = f"Changement d'état de l'action {record.name}"
                body = f"""
                <p>Bonjour,</p>
                <p>L'état de l'action corrective/préventive {record.name} a changé vers "{dict(record._fields['state'].selection).get(record.state)}".</p>
                <p>Cordialement,</p>
                """

                record.message_post(
                    body=body,
                    subject=subject,
                    partner_ids=recipients,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )

    # Méthode pour vérifier les délais de clôture et envoyer des alertes
    @api.model
    def _cron_check_closure_deadlines(self):
        today = fields.Date.today()
        # Rechercher les actions avec une date de clôture dans 4 jours et pas encore clôturées
        records = self.search([
            ('closure_deadline', '=', today + timedelta(days=4)),
            ('state', '!=', 'termine')
        ])

        for record in records:
            recipients = []

            if record.closure_responsible_id and record.closure_responsible_id.partner_id:
                recipients.append(record.closure_responsible_id.partner_id.id)

            if record.responsible_id and record.responsible_id.partner_id:
                recipients.append(record.responsible_id.partner_id.id)

            if recipients:
                subject = f"Rappel: Date limite de clôture approche pour l'action {record.name}"
                body = f"""
                <p>Bonjour,</p>
                <p>La date limite de clôture pour l'action corrective/préventive {record.name} est dans 4 jours ({record.closure_deadline}).</p>
                <p>Veuillez prendre les mesures nécessaires pour finaliser cette action.</p>
                <p>Cordialement,</p>
                """

                record.message_post(
                    body=body,
                    subject=subject,
                    partner_ids=recipients,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )

    # Options de notification
    def action_set_draft(self):
        self.state = 'draft'

    def action_set_en_attente(self):
        self.state = 'en_attente'

    def action_set_en_cours(self):
        self.state = 'en_cours'

    def action_set_bloque(self):
        self.state = 'bloque'

    def action_set_termine(self):
        self.state = 'termine'

    def action_set_cancel(self):
        self.state = 'cancel'

    def action_assign_responsible(self):
        """
        Cette méthode est appelée lorsque l'utilisateur clique sur le bouton 'Assigner'
        à côté du champ responsible_id. Elle assigne l'utilisateur actuel comme responsable.
        """
        self.ensure_one()
        self.write({
            'responsible_id': self.env.user.employee_id.id if self.env.user.employee_id else False
        })

        # Optionnel: Ajouter un message dans le chatter pour tracer l'action
        self.message_post(
            body=("Le responsable a été défini comme %s") % self.env.user.name,
            message_type='notification'
        )

        return True

    # Méthode qui change l'état à 'termine' et enregistre la date
    def action_clore(self):
        """ Change l'état à 'termine' et enregistre la date de clôture """
        for rec in self:
            rec.state = 'termine'
            rec.date_cloture = datetime.now()

    @api.model
    def create(self, vals):
        record = super(Action, self).create(vals)
        self._log_modification(record, 'create')
        return record

    def write(self, vals):
        result = super(Action, self).write(vals)
        for record in self:
            self._log_modification(record, 'update', vals)
        return result

    def _log_modification(self, record, action_type, vals=None):
        modification_vals = {
            'user_id': self.env.user.id,
            'model_name': self._name,
            'record_id': record.id,
            'action_type': action_type,
            'change_date': fields.Datetime.now()
        }

        if action_type == 'update' and vals:
            for field, new_value in vals.items():
                if field in record:  # Vérifiez que le champ existe
                    old_state = record[field]
                    if old_state != new_value:
                        mod_vals = modification_vals.copy()
                        mod_vals.update({
                            'field_name': field,
                            'old_state': str(old_state),
                            'new_state': str(new_value),
                        })
                        self.env['action.corrective.history'].create(mod_vals)

        if action_type == 'create':
            self.env['action.corrective.history'].create(modification_vals)
