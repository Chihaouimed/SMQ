# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SatisfactionReportWizard(models.TransientModel):
    _name = 'satisfaction.report.wizard'
    _description = 'Rapport d\'Analyse de Satisfaction IA'

    enquete_id = fields.Many2one('enquete.satisfaction', string='Enquête', required=True)

    # Données du rapport
    satisfaction_score = fields.Float(string="Score Global", related='enquete_id.satisfaction_score')
    satisfaction_level = fields.Selection(related='enquete_id.satisfaction_level', string="Niveau")
    response_count = fields.Integer(string="Réponses", related='enquete_id.response_count')
    positive_responses = fields.Integer(string="Positives", related='enquete_id.positive_responses')
    negative_responses = fields.Integer(string="Négatives", related='enquete_id.negative_responses')
    neutral_responses = fields.Integer(string="Neutres", related='enquete_id.neutral_responses')

    # Analyses détaillées
    satisfaction_summary = fields.Html(string="Résumé Exécutif", compute='_compute_formatted_content')
    positive_points = fields.Html(string="Points Positifs", compute='_compute_formatted_content')
    negative_points = fields.Html(string="Points d'Amélioration", compute='_compute_formatted_content')
    recommended_actions = fields.Html(string="Actions Recommandées", compute='_compute_formatted_content')
    question_analysis = fields.Html(string="Analyse par Question", compute='_compute_formatted_content')

    # Métadonnées
    analysis_date = fields.Datetime(string="Date d'Analyse", related='enquete_id.analysis_date')
    total_clients = fields.Integer(string="Clients Invités", compute='_compute_stats')
    response_rate = fields.Float(string="Taux de Réponse (%)", compute='_compute_stats')

    @api.depends('enquete_id')
    def _compute_stats(self):
        for record in self:
            if record.enquete_id:
                record.total_clients = len(record.enquete_id.client_ids)
                if record.total_clients > 0:
                    record.response_rate = (record.response_count / record.total_clients) * 100
                else:
                    record.response_rate = 0
            else:
                record.total_clients = 0
                record.response_rate = 0

    @api.depends('enquete_id', 'enquete_id.satisfaction_summary', 'enquete_id.positive_points',
                 'enquete_id.negative_points', 'enquete_id.recommended_actions', 'enquete_id.question_analysis')
    def _compute_formatted_content(self):
        for record in self:
            if not record.enquete_id:
                record.satisfaction_summary = "<p>Aucune donnée disponible</p>"
                record.positive_points = "<p>Aucune donnée disponible</p>"
                record.negative_points = "<p>Aucune donnée disponible</p>"
                record.recommended_actions = "<p>Aucune donnée disponible</p>"
                record.question_analysis = "<p>Aucune donnée disponible</p>"
                continue

            # Résumé formaté
            summary = record.enquete_id.satisfaction_summary or "Aucun résumé disponible"
            record.satisfaction_summary = f"""
            <div class="o_field_html">
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 10px 0;">
                    <h4 style="color: #007bff; margin-top: 0;">📊 Résumé de l'Analyse</h4>
                    <pre style="white-space: pre-wrap; font-family: inherit; background: white; padding: 10px; border-radius: 5px;">{summary}</pre>
                </div>
            </div>
            """

            # Points positifs formatés
            positive = record.enquete_id.positive_points or "Aucun point positif identifié"
            points_list = positive.split('\n• ') if positive.startswith('•') else positive.split('\n')
            positive_html = ""
            for point in points_list:
                if point.strip():
                    clean_point = point.replace('• ', '').strip()
                    if clean_point:
                        positive_html += f"<li style='margin: 8px 0; color: #28a745;'><strong>✅</strong> {clean_point}</li>"

            record.positive_points = f"""
            <div class="o_field_html">
                <div style="background: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 10px 0;">
                    <h4 style="color: #155724; margin-top: 0;">🌟 Points Positifs Identifiés</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        {positive_html if positive_html else '<li>Aucun point positif spécifique identifié</li>'}
                    </ul>
                </div>
            </div>
            """

            # Points négatifs formatés
            negative = record.enquete_id.negative_points or "Aucun point négatif identifié"
            neg_points_list = negative.split('\n• ') if negative.startswith('•') else negative.split('\n')
            negative_html = ""
            for point in neg_points_list:
                if point.strip():
                    clean_point = point.replace('• ', '').strip()
                    if clean_point:
                        negative_html += f"<li style='margin: 8px 0; color: #dc3545;'><strong>⚠️</strong> {clean_point}</li>"

            record.negative_points = f"""
            <div class="o_field_html">
                <div style="background: #f8d7da; padding: 15px; border-left: 4px solid #dc3545; margin: 10px 0;">
                    <h4 style="color: #721c24; margin-top: 0;">🔧 Points d'Amélioration</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        {negative_html if negative_html else '<li>Aucun point négatif spécifique identifié</li>'}
                    </ul>
                </div>
            </div>
            """

            # Actions recommandées formatées
            actions = record.enquete_id.recommended_actions or "Aucune recommandation disponible"
            action_list = actions.split('\n• ') if actions.startswith('•') else actions.split('\n')
            actions_html = ""
            priority_colors = {
                '🚨': '#dc3545',  # Urgent - Rouge
                '⚠️': '#fd7e14',  # Important - Orange
                '✅': '#28a745',  # Normal - Vert
                '🎉': '#17a2b8',  # Positif - Bleu
                '📞': '#6f42c1',  # Contact - Violet
                '🔍': '#20c997',  # Analyse - Teal
                '📈': '#ffc107',  # Amélioration - Jaune
            }

            for action in action_list:
                if action.strip():
                    clean_action = action.replace('• ', '').strip()
                    if clean_action:
                        # Déterminer la couleur basée sur l'emoji
                        color = '#6c757d'  # Couleur par défaut
                        for emoji, emoji_color in priority_colors.items():
                            if emoji in clean_action:
                                color = emoji_color
                                break

                        actions_html += f"""
                        <li style='margin: 10px 0; padding: 8px; background: rgba(0,0,0,0.05); border-radius: 5px; border-left: 3px solid {color};'>
                            <span style='color: {color}; font-weight: bold;'>{clean_action}</span>
                        </li>
                        """

            record.recommended_actions = f"""
            <div class="o_field_html">
                <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 10px 0;">
                    <h4 style="color: #856404; margin-top: 0;">💡 Actions Recommandées par l'IA</h4>
                    <ul style="margin: 0; padding-left: 20px; list-style: none;">
                        {actions_html if actions_html else '<li>Aucune recommandation spécifique</li>'}
                    </ul>
                </div>
            </div>
            """

            # Analyse par questions formatée
            questions = record.enquete_id.question_analysis or "Aucune analyse par question disponible"
            record.question_analysis = f"""
            <div class="o_field_html">
                <div style="background: #e2e3e5; padding: 15px; border-left: 4px solid #6c757d; margin: 10px 0;">
                    <h4 style="color: #495057; margin-top: 0;">📋 Analyse Détaillée par Question</h4>
                    <pre style="white-space: pre-wrap; font-family: inherit; background: white; padding: 10px; border-radius: 5px;">{questions}</pre>
                </div>
            </div>
            """

    def action_export_report(self):
        """Exporte le rapport au format PDF"""
        self.ensure_one()
        return self.env.ref('votre_module.satisfaction_report_template').report_action(self)

    def action_send_report_by_email(self):
        """Envoie le rapport par email"""
        self.ensure_one()

        # Créer le contenu HTML du rapport pour l'email
        email_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
            <h1 style="color: #007bff; text-align: center;">📊 Rapport d'Analyse de Satisfaction IA</h1>
            <h2 style="color: #6c757d;">Enquête: {self.enquete_id.reference}</h2>

            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3>🎯 Résultats Clés</h3>
                <ul>
                    <li><strong>Score de satisfaction:</strong> {self.satisfaction_score * 100:.1f}%</li>
                    <li><strong>Niveau:</strong> {dict(self.enquete_id._fields['satisfaction_level'].selection).get(self.satisfaction_level)}</li>
                    <li><strong>Taux de réponse:</strong> {self.response_rate:.1f}% ({self.response_count}/{self.total_clients})</li>
                    <li><strong>Répartition:</strong> {self.positive_responses} positives, {self.negative_responses} négatives, {self.neutral_responses} neutres</li>
                </ul>
            </div>

            {self.satisfaction_summary}
            {self.positive_points}
            {self.negative_points}
            {self.recommended_actions}

            <div style="text-align: center; margin-top: 30px; color: #6c757d;">
                <small>Rapport généré le {fields.Datetime.now().strftime('%d/%m/%Y à %H:%M')}</small>
            </div>
        </div>
        """

        # Créer et envoyer l'email
        mail_values = {
            'subject': f'Rapport de Satisfaction IA - {self.enquete_id.reference}',
            'body_html': email_content,
            'email_to': self.env.user.email,
            'email_from': self.env.company.email or self.env.user.email,
        }

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '📧 Rapport envoyé',
                'message': f'Le rapport a été envoyé à {self.env.user.email}',
                'type': 'success',
            }
        }

    def action_back_to_survey(self):
        """Retourne à l'enquête"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'enquete.satisfaction',
            'res_id': self.enquete_id.id,
            'view_mode': 'form',
            'target': 'current',
        }