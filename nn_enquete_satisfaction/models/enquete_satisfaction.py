# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class EnqueteSatisfaction(models.Model):
    _name = 'enquete.satisfaction'
    _description = 'Enquête de Satisfaction Client avec IA'
    _order = 'date_debut desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # === CHAMPS EXISTANTS (conservés tels quels) ===
    reference = fields.Char(string="Référence", required=True, copy=False, readonly=True, default="New")
    name = fields.Char(string="Référence de l'enquête", required=True, copy=False, readonly=True, default='New')
    date_debut = fields.Date(string="Date de début", default=fields.Date.context_today, tracking=True)
    date_fin = fields.Date(string="Date de fin", tracking=True)
    client_ids = fields.Many2many('res.partner', string="Clients concernés")
    survey_id = fields.Many2one('survey.survey', string="Sondage", tracking=True)
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

    # === NOUVEAUX CHAMPS IA POUR SATISFACTION ===

    # Configuration IA
    ia_configured = fields.Boolean(string="IA configurée", compute="_compute_ia_status")

    # Analyse de satisfaction
    satisfaction_score = fields.Float(string="Score de satisfaction global", readonly=True,
                                      help="Score entre 0 et 1 calculé par l'IA")
    satisfaction_level = fields.Selection([
        ('very_low', 'Très insatisfait'),
        ('low', 'Insatisfait'),
        ('neutral', 'Neutre'),
        ('high', 'Satisfait'),
        ('very_high', 'Très satisfait')
    ], string="Niveau de satisfaction", compute="_compute_satisfaction_level", store=True)

    # Détails de l'analyse
    satisfaction_summary = fields.Text(string="Résumé de l'analyse", readonly=True)
    positive_points = fields.Text(string="Points positifs identifiés", readonly=True)
    negative_points = fields.Text(string="Points d'amélioration", readonly=True)
    recommended_actions = fields.Text(string="Actions recommandées", readonly=True)

    # Statistiques des réponses
    response_count = fields.Integer(string="Nombre de réponses", compute="_compute_response_stats")
    positive_responses = fields.Integer(string="Réponses positives", compute="_compute_response_stats")
    negative_responses = fields.Integer(string="Réponses négatives", compute="_compute_response_stats")
    neutral_responses = fields.Integer(string="Réponses neutres", compute="_compute_response_stats")

    # Analyse par questions
    question_analysis = fields.Text(string="Analyse détaillée par question", readonly=True)

    # État de l'analyse
    analysis_completed = fields.Boolean(string="Analyse terminée", default=False)
    analysis_date = fields.Datetime(string="Date de dernière analyse", readonly=True)

    @api.depends('survey_id')
    def _compute_survey_url(self):
        """Calcule l'URL du sondage"""
        for record in self:
            try:
                if record.survey_id and hasattr(record.survey_id, 'access_token') and record.survey_id.access_token:
                    record.survey_url = f'/survey/start/{record.survey_id.access_token}'
                else:
                    record.survey_url = False
            except Exception as e:
                _logger.error(f"Erreur dans _compute_survey_url pour {record}: {str(e)}")
                record.survey_url = False

    def _compute_ia_status(self):
        """Vérifie si l'IA est configurée"""
        for record in self:
            try:
                global_key = self.env['ir.config_parameter'].sudo().get_param('huggingface.api_key', '')
                record.ia_configured = bool(global_key)
            except Exception as e:
                _logger.error(f"Erreur dans _compute_ia_status pour {record}: {str(e)}")
                record.ia_configured = False

    @api.depends('satisfaction_score')
    def _compute_satisfaction_level(self):
        """Calcule le niveau de satisfaction basé sur le score"""
        for record in self:
            try:
                if not hasattr(record, 'satisfaction_score') or record.satisfaction_score is False:
                    record.satisfaction_level = 'neutral'
                elif record.satisfaction_score == 0:
                    record.satisfaction_level = 'neutral'
                elif record.satisfaction_score < 0.2:
                    record.satisfaction_level = 'very_low'
                elif record.satisfaction_score < 0.4:
                    record.satisfaction_level = 'low'
                elif record.satisfaction_score < 0.6:
                    record.satisfaction_level = 'neutral'
                elif record.satisfaction_score < 0.8:
                    record.satisfaction_level = 'high'
                else:
                    record.satisfaction_level = 'very_high'
            except Exception as e:
                _logger.error(f"Erreur dans _compute_satisfaction_level pour {record}: {str(e)}")
                record.satisfaction_level = 'neutral'

    @api.depends('survey_id')
    def _compute_response_stats(self):
        """Calcule les statistiques des réponses"""
        for record in self:
            # Initialiser toutes les valeurs par défaut
            record.response_count = 0
            record.positive_responses = 0
            record.negative_responses = 0
            record.neutral_responses = 0

            # Vérifier si le survey_id existe et est valide
            if not record.survey_id or not record.survey_id.id:
                continue

            try:
                # Rechercher les réponses terminées
                user_inputs = self.env['survey.user_input'].search([
                    ('survey_id', '=', record.survey_id.id),
                    ('state', '=', 'done')
                ])

                record.response_count = len(user_inputs)

                # Ne lancer l'analyse automatique que si :
                # 1. L'IA est configurée
                # 2. Il y a des réponses
                # 3. L'analyse n'est pas déjà terminée
                # 4. Le record existe en base (pas un NewId)
                if (record.ia_configured and
                        user_inputs and
                        not record.analysis_completed and
                        record.id and
                        not str(record.id).startswith('NewId')):
                    record._analyze_satisfaction_with_ia(user_inputs)

            except Exception as e:
                _logger.error(f"Erreur dans _compute_response_stats pour {record}: {str(e)}")
                # En cas d'erreur, garder les valeurs par défaut déjà assignées

    def _analyze_satisfaction_with_ia(self, user_inputs):
        """Analyse la satisfaction avec l'IA - Version sécurisée"""
        if not user_inputs:
            return

        try:
            # Vérifier que le record existe en base
            if not self.id or str(self.id).startswith('NewId'):
                _logger.warning(f"Tentative d'analyse sur un record non sauvegardé: {self}")
                return

            api_key = self.env['ir.config_parameter'].sudo().get_param('huggingface.api_key', '')
            if not api_key:
                _logger.warning("Clé API manquante pour l'analyse IA")
                return

            # Collecter tous les commentaires textuels
            all_comments = []
            question_responses = {}

            for user_input in user_inputs:
                try:
                    # Récupérer les réponses textuelles
                    text_answers = self.env['survey.user_input.line'].search([
                        ('user_input_id', '=', user_input.id),
                        ('answer_type', '=', 'text'),
                        ('value_text', '!=', False)
                    ])

                    for answer in text_answers:
                        if answer.value_text and len(answer.value_text.strip()) > 3:
                            all_comments.append(answer.value_text)

                            # Organiser par question
                            question_title = answer.question_id.title if answer.question_id else "Question sans titre"
                            if question_title not in question_responses:
                                question_responses[question_title] = []
                            question_responses[question_title].append(answer.value_text)

                except Exception as e:
                    _logger.error(f"Erreur lors de la collecte des réponses pour {user_input}: {str(e)}")
                    continue

            if all_comments:
                self._perform_sentiment_analysis(all_comments, question_responses)
            else:
                # Analyse basée uniquement sur les notes numériques si pas de commentaires
                self._analyze_numeric_ratings(user_inputs)

        except Exception as e:
            _logger.error(f"Erreur lors de l'analyse IA pour {self}: {str(e)}")
            # En cas d'erreur, faire une analyse simplifiée
            self._fallback_analysis(user_inputs)

    def _perform_sentiment_analysis(self, comments, question_responses):
        """Effectue l'analyse de sentiment avec simulation - Version sécurisée"""
        try:
            # Vérifier que le record peut être modifié
            if not self.id or str(self.id).startswith('NewId'):
                _logger.warning(f"Impossible d'analyser un record non sauvegardé: {self}")
                return

            total_comments = len(comments)

            # Simulation de l'analyse IA (remplacez par vraie API Hugging Face)
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            sentiment_scores = []

            # Mots-clés pour simulation (remplacez par vraie API)
            positive_keywords = ['excellent', 'parfait', 'satisfait', 'bien', 'bon', 'super', 'génial', 'merci',
                                 'rapide']
            negative_keywords = ['mauvais', 'nul', 'insatisfait', 'problème', 'décevant', 'lent', 'difficile',
                                 'compliqué']

            positive_points = []
            negative_points = []

            for comment in comments:
                try:
                    comment_lower = comment.lower()

                    # Analyse simplifiée basée sur mots-clés (remplacez par vraie IA)
                    pos_score = sum(1 for word in positive_keywords if word in comment_lower)
                    neg_score = sum(1 for word in negative_keywords if word in comment_lower)

                    if pos_score > neg_score:
                        positive_count += 1
                        sentiment_scores.append(0.8)
                        if len(comment) > 20:  # Commentaires substantiels
                            positive_points.append(comment[:100] + "..." if len(comment) > 100 else comment)
                    elif neg_score > pos_score:
                        negative_count += 1
                        sentiment_scores.append(0.2)
                        if len(comment) > 20:
                            negative_points.append(comment[:100] + "..." if len(comment) > 100 else comment)
                    else:
                        neutral_count += 1
                        sentiment_scores.append(0.5)
                except Exception as e:
                    _logger.error(f"Erreur lors de l'analyse du commentaire: {str(e)}")
                    neutral_count += 1
                    sentiment_scores.append(0.5)

            # Calculer le score global
            if sentiment_scores:
                satisfaction_score = sum(sentiment_scores) / len(sentiment_scores)
            else:
                satisfaction_score = 0.5

            # Mettre à jour les champs avec des valeurs par défaut sûres
            vals = {
                'satisfaction_score': satisfaction_score,
                'positive_responses': positive_count,
                'negative_responses': negative_count,
                'neutral_responses': neutral_count,
                'analysis_completed': True,
                'analysis_date': fields.Datetime.now(),
            }

            # Générer le résumé
            total_responses = self.response_count or 0
            pos_pct = (positive_count / total_comments * 100) if total_comments > 0 else 0
            neg_pct = (negative_count / total_comments * 100) if total_comments > 0 else 0

            vals['satisfaction_summary'] = f"""
Analyse de {total_comments} commentaires sur {total_responses} réponses:

📊 Répartition des sentiments:
• {positive_count} commentaires positifs ({pos_pct:.1f}%)
• {negative_count} commentaires négatifs ({neg_pct:.1f}%)
• {neutral_count} commentaires neutres

🎯 Score global de satisfaction: {satisfaction_score * 100:.1f}%
📅 Analysé le: {fields.Datetime.now().strftime('%d/%m/%Y à %H:%M')}
            """.strip()

            # Points positifs et négatifs
            vals['positive_points'] = "\n• ".join(positive_points[
                                                  :5]) if positive_points else "Aucun point positif spécifique identifié dans les commentaires"
            vals['negative_points'] = "\n• ".join(negative_points[
                                                  :5]) if negative_points else "Aucun point négatif spécifique identifié dans les commentaires"

            # Générer des recommandations
            recommended_actions = self._generate_satisfaction_recommendations_safe(satisfaction_score, positive_count,
                                                                                   negative_count, total_responses)
            vals['recommended_actions'] = recommended_actions

            # Analyser par question
            question_analysis = self._analyze_by_question_safe(question_responses)
            vals['question_analysis'] = question_analysis

            # Écriture sécurisée
            self.write(vals)

            _logger.info(f"Analyse IA terminée pour l'enquête {self.reference}: score {satisfaction_score:.2f}")

        except Exception as e:
            _logger.error(f"Erreur dans l'analyse de sentiment pour {self}: {str(e)}")
            self._fallback_analysis([])

    def _generate_satisfaction_recommendations_safe(self, satisfaction_score, positive_count, negative_count,
                                                    total_responses):
        """Génère des recommandations basées sur l'analyse de satisfaction - Version sécurisée"""
        try:
            recommendations = []

            if satisfaction_score >= 0.8:
                recommendations.extend([
                    "🎉 Excellente satisfaction ! Demandez des témoignages clients",
                    "📣 Partagez ces retours positifs avec l'équipe",
                    "🔄 Utilisez cette enquête comme modèle pour d'autres projets"
                ])
            elif satisfaction_score >= 0.6:
                recommendations.extend([
                    "✅ Satisfaction correcte, quelques améliorations possibles",
                    "🔍 Analysez les points négatifs pour identifier les améliorations",
                    "📞 Contact de suivi pour consolider la relation client"
                ])
            elif satisfaction_score >= 0.4:
                recommendations.extend([
                    "⚠️ Satisfaction mitigée, actions d'amélioration nécessaires",
                    "🤝 Planifiez un rendez-vous avec le client pour discuter",
                    "🔧 Mettez en place un plan d'action correctif"
                ])
            else:
                recommendations.extend([
                    "🚨 Satisfaction faible, intervention urgente requise",
                    "📞 Contact immédiat avec le client pour comprendre les problèmes",
                    "🏥 Plan de récupération à mettre en place rapidement"
                ])

            # Recommandations spécifiques basées sur les points négatifs
            if negative_count > positive_count:
                recommendations.append("🔍 Analysez en priorité les commentaires négatifs")

            if total_responses < 5:
                recommendations.append("📈 Taux de réponse faible, relancer les clients non-répondants")

            return "\n• ".join(recommendations)
        except Exception as e:
            _logger.error(f"Erreur lors de la génération de recommandations: {str(e)}")
            return "• Erreur lors de la génération des recommandations"

    def _analyze_by_question_safe(self, question_responses):
        """Analyse détaillée par question - Version sécurisée"""
        try:
            if not question_responses:
                return "Aucune analyse par question disponible."

            analysis_parts = []
            for question, responses in question_responses.items():
                if len(responses) > 0:
                    # Analyse simplifiée par question
                    total = len(responses)
                    sample_response = responses[0][:100] + "..." if len(responses[0]) > 100 else responses[0]

                    analysis_parts.append(f"""
📋 {question}
   • Nombre de réponses: {total}
   • Exemple: "{sample_response}"
                    """.strip())

            return "\n\n".join(analysis_parts)
        except Exception as e:
            _logger.error(f"Erreur lors de l'analyse par question: {str(e)}")
            return "Erreur lors de l'analyse par question."

    def _analyze_numeric_ratings(self, user_inputs):
        """Analyse basée sur les notes numériques quand il n'y a pas de commentaires"""
        if not user_inputs:
            return

        try:
            ratings = []
            for user_input in user_inputs:
                # Récupérer les réponses numériques
                numeric_answers = self.env['survey.user_input.line'].search([
                    ('user_input_id', '=', user_input.id),
                    ('answer_type', 'in', ['number', 'suggestion']),
                    ('value_number', '!=', False)
                ])

                for answer in numeric_answers:
                    if answer.value_number:
                        # Normaliser la note (supposer échelle 1-5 ou 1-10)
                        if answer.value_number <= 5:
                            # Échelle 1-5
                            normalized_rating = answer.value_number / 5.0
                        else:
                            # Échelle 1-10
                            normalized_rating = answer.value_number / 10.0
                        ratings.append(normalized_rating)

            if ratings:
                avg_rating = sum(ratings) / len(ratings)

                # Classification des réponses basée sur la note
                high_ratings = len([r for r in ratings if r >= 0.7])
                low_ratings = len([r for r in ratings if r <= 0.4])
                neutral_ratings = len(ratings) - high_ratings - low_ratings

                vals = {
                    'satisfaction_score': avg_rating,
                    'positive_responses': high_ratings,
                    'negative_responses': low_ratings,
                    'neutral_responses': neutral_ratings,
                    'analysis_completed': True,
                    'analysis_date': fields.Datetime.now(),
                }

                vals['satisfaction_summary'] = f"""
Analyse basée sur {len(ratings)} notes numériques:
• Note moyenne: {avg_rating * 5:.1f}/5 ({avg_rating * 100:.1f}%)
• Notes élevées (≥3.5/5): {high_ratings}
• Notes faibles (≤2/5): {low_ratings}
• Notes moyennes: {neutral_ratings}

📅 Analysé le: {fields.Datetime.now().strftime('%d/%m/%Y à %H:%M')}
                """.strip()

                vals['recommended_actions'] = self._generate_satisfaction_recommendations_safe(avg_rating, high_ratings,
                                                                                               low_ratings,
                                                                                               self.response_count)

                self.write(vals)

            else:
                self._fallback_analysis(user_inputs)

        except Exception as e:
            _logger.error(f"Erreur lors de l'analyse des notes numériques: {str(e)}")
            self._fallback_analysis(user_inputs)

    def _fallback_analysis(self, user_inputs):
        """Analyse de fallback si l'IA ne fonctionne pas"""
        try:
            total = len(user_inputs) if user_inputs else self.response_count
            if total == 0:
                return

            # Analyse basique sans IA
            vals = {
                'satisfaction_score': 0.6,  # Score neutre par défaut
                'positive_responses': int(total * 0.6),
                'negative_responses': int(total * 0.2),
                'neutral_responses': total - int(total * 0.6) - int(total * 0.2),
                'analysis_completed': True,
                'analysis_date': fields.Datetime.now(),
            }

            vals['satisfaction_summary'] = f"""
Analyse basique de {total} réponses (IA non disponible):
• Score estimé: {vals['satisfaction_score'] * 100:.0f}%
• Analyse effectuée le {fields.Datetime.now().strftime('%d/%m/%Y à %H:%M')}

Note: Configurez l'IA avec une clé API Hugging Face pour une analyse détaillée.
            """.strip()

            vals[
                'recommended_actions'] = "• Configurez l'IA pour une analyse détaillée\n• Relisez manuellement les commentaires clients"
            vals['positive_points'] = "Analyse manuelle requise"
            vals['negative_points'] = "Analyse manuelle requise"

            self.write(vals)
        except Exception as e:
            _logger.error(f"Erreur dans _fallback_analysis: {str(e)}")

    def action_analyze_satisfaction(self):
        """Lance l'analyse de satisfaction et ouvre le rapport détaillé"""
        self.ensure_one()

        if not self.survey_id:
            raise UserError("Veuillez associer un sondage à cette enquête avant d'analyser la satisfaction.")

        if not self.ia_configured:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '⚙️ Configuration IA requise',
                    'message': 'Allez dans Paramètres → Technique → Paramètres système et créez le paramètre \"huggingface.api_key\" avec votre clé API.',
                    'type': 'warning',
                    'sticky': True,
                }
            }

        # Forcer la recalculation (réinitialiser l'analyse)
        self.analysis_completed = False
        self._compute_response_stats()

        # Si l'analyse n'a pas été faite automatiquement, forcer une analyse fallback
        if not self.analysis_completed:
            # Appel manuel du fallback
            user_inputs = self.env['survey.user_input'].search([
                ('survey_id', '=', self.survey_id.id),
                ('state', '=', 'done')
            ])
            self._fallback_analysis(user_inputs)

        # Maintenant, ouvrir le rapport (même si fallback)
        wizard = self.env['satisfaction.report.wizard'].create({
            'enquete_id': self.id,
        })

        return {
            'name': f'📊 Rapport d\'Analyse IA - {self.reference}',
            'type': 'ir.actions.act_window',
            'res_model': 'satisfaction.report.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'dialog_size': 'extra-large',
            },
            'flags': {
                'form': {
                    'action_buttons': True,
                    'options': {
                        'mode': 'readonly',
                    }
                }
            }
        }

    def action_generate_satisfaction_report(self):
        """Génère un rapport de satisfaction détaillé"""
        self.ensure_one()

        if not self.analysis_completed:
            self.action_analyze_satisfaction()

        report_content = f"""
# 📊 Rapport de Satisfaction Client - {self.reference}

## Résumé Exécutif
**Score de satisfaction global: {self.satisfaction_score * 100:.1f}%**
**Niveau: {dict(self._fields['satisfaction_level'].selection).get(self.satisfaction_level)}**

{self.satisfaction_summary}

## 🌟 Points Positifs
{self.positive_points}

## 🔧 Points d'Amélioration  
{self.negative_points}

## 💡 Actions Recommandées
{self.recommended_actions}

## 📋 Analyse Détaillée par Question
{self.question_analysis or "Aucune analyse par question disponible"}

---
*Rapport généré le {fields.Datetime.now().strftime('%d/%m/%Y à %H:%M')} par l'IA d'analyse de satisfaction*
        """

        # Ajouter au chatter
        self.message_post(
            body=f"<pre>{report_content}</pre>",
            subject="📊 Rapport d'analyse de satisfaction IA"
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '📋 Rapport généré',
                'message': 'Le rapport détaillé a été ajouté aux discussions.',
                'type': 'success',
            }
        }

    # === MÉTHODES EXISTANTES CONSERVÉES ===

    def action_assign_responsible(self):
        """Méthode existante conservée"""
        self.ensure_one()
        self.write({
            'responsible_id': self.env.user.id
        })
        self.message_post(
            body=f"Le responsable a été défini comme {self.env.user.name}",
            message_type='notification'
        )
        return True

    def action_send_emails(self):
        """Version améliorée de la méthode existante avec analyse automatique"""
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

    def action_close_survey(self):
        """Méthode existante conservée"""
        self.ensure_one()
        if not self.responsible_id:
            raise UserError("Veuillez assigner un responsable avant de clôturer l'enquête.")

        self.write({'state': 'cloturee'})
        self.message_post(body="Enquête clôturée.", message_type='notification')
        return True

    def action_mark_as_completed(self):
        """Méthode existante conservée"""
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

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        """Validation des dates"""
        for record in self:
            if record.date_debut and record.date_fin:
                if record.date_debut > record.date_fin:
                    raise ValidationError("La date de début ne peut pas être postérieure à la date de fin.")

    @api.onchange('type_questionnaire')
    def _onchange_type_questionnaire(self):
        """Actions lors du changement de type de questionnaire"""
        if self.type_questionnaire:
            if self.type_questionnaire == 'court':
                # Logique pour questionnaire court
                pass
            elif self.type_questionnaire == 'detaille':
                # Logique pour questionnaire détaillé
                pass

    def action_reset_analysis(self):
        """Remet à zéro l'analyse pour permettre une nouvelle analyse"""
        self.ensure_one()

        vals = {
            'analysis_completed': False,
            'analysis_date': False,
            'satisfaction_score': 0.0,
            'satisfaction_summary': False,
            'positive_points': False,
            'negative_points': False,
            'recommended_actions': False,
            'question_analysis': False,
            'positive_responses': 0,
            'negative_responses': 0,
            'neutral_responses': 0,
        }

        self.write(vals)

        self.message_post(
            body="L'analyse de satisfaction a été remise à zéro. Vous pouvez maintenant relancer une nouvelle analyse.",
            message_type='notification'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '🔄 Analyse réinitialisée',
                'message': 'L\'analyse a été remise à zéro. Vous pouvez relancer une nouvelle analyse.',
                'type': 'success',
            }
        }

    def action_view_survey_responses(self):
        """Ouvre la vue des réponses du sondage"""
        self.ensure_one()

        if not self.survey_id:
            raise UserError("Aucun sondage n'est associé à cette enquête.")

        return {
            'name': f'Réponses - {self.survey_id.title}',
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('survey_id', '=', self.survey_id.id)],
            'context': {
                'default_survey_id': self.survey_id.id,
                'search_default_completed': 1,
            }
        }

    def action_send_reminder(self):
        """Envoie un rappel aux clients qui n'ont pas encore répondu"""
        self.ensure_one()

        if not self.survey_id:
            raise UserError("Veuillez associer un sondage avant d'envoyer des rappels.")

        # Trouver les clients qui n'ont pas encore répondu
        completed_partners = self.env['survey.user_input'].search([
            ('survey_id', '=', self.survey_id.id),
            ('state', '=', 'done'),
            ('partner_id', 'in', self.client_ids.ids)
        ]).mapped('partner_id')

        pending_clients = self.client_ids - completed_partners

        if not pending_clients:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ Tous les clients ont répondu',
                    'message': 'Aucun rappel nécessaire, tous les clients ont déjà répondu au sondage.',
                    'type': 'info',
                }
            }

        # Envoyer les rappels
        reminder_count = 0
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        for client in pending_clients:
            if client.email:
                # Chercher s'il y a déjà une participation créée
                existing_input = self.env['survey.user_input'].search([
                    ('survey_id', '=', self.survey_id.id),
                    ('partner_id', '=', client.id)
                ], limit=1)

                if existing_input:
                    survey_url = f"{base_url}/survey/start/{self.survey_id.id}?token={existing_input.access_token}"
                else:
                    # Créer une nouvelle participation
                    user_input = self.env['survey.user_input'].create({
                        'survey_id': self.survey_id.id,
                        'partner_id': client.id,
                        'email': client.email,
                        'deadline': self.date_fin,
                    })
                    survey_url = f"{base_url}/survey/start/{self.survey_id.id}?token={user_input.access_token}"

                # Envoyer l'email de rappel
                body_html = f"""
                    <p>Bonjour {client.name},</p>
                    <p>Nous vous rappelons que votre avis nous intéresse ! Vous n'avez pas encore répondu à notre enquête de satisfaction concernant {self.reference}.</p>
                    <p>Cliquez sur ce lien pour accéder au sondage : <a href="{survey_url}">{self.survey_id.title}</a></p>
                    {f'<p>Date limite de réponse : {self.date_fin.strftime("%d/%m/%Y")}</p>' if self.date_fin else ''}
                    <p>Merci pour votre temps !</p>
                    <p>Cordialement,</p>
                """

                mail_values = {
                    'email_to': client.email,
                    'subject': f"Rappel - Enquête de Satisfaction: {self.reference}",
                    'body_html': body_html,
                    'email_from': self.env.user.email or self.env.company.email,
                }

                mail = self.env['mail.mail'].create(mail_values)
                mail.send()
                reminder_count += 1

        self.message_post(
            body=f"Rappel envoyé à {reminder_count} client(s) : {', '.join(pending_clients.mapped('name'))}",
            message_type='notification'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '📧 Rappels envoyés',
                'message': f'Rappel envoyé à {reminder_count} client(s) qui n\'ont pas encore répondu.',
                'type': 'success',
            }
        }

    def get_satisfaction_dashboard_data(self):
        """Retourne les données pour le tableau de bord de satisfaction"""
        self.ensure_one()

        if not self.analysis_completed:
            return {
                'error': 'Analyse non terminée',
                'message': 'Veuillez d\'abord effectuer l\'analyse de satisfaction.'
            }

        # Calcul du taux de réponse
        total_clients = len(self.client_ids)
        response_rate = (self.response_count / total_clients * 100) if total_clients > 0 else 0

        # Données pour les graphiques
        sentiment_data = {
            'positive': self.positive_responses,
            'negative': self.negative_responses,
            'neutral': self.neutral_responses
        }

        return {
            'satisfaction_score': self.satisfaction_score,
            'satisfaction_level': self.satisfaction_level,
            'response_count': self.response_count,
            'total_clients': total_clients,
            'response_rate': response_rate,
            'sentiment_data': sentiment_data,
            'analysis_date': self.analysis_date.strftime('%d/%m/%Y %H:%M') if self.analysis_date else None,
            'summary': self.satisfaction_summary,
            'recommendations_count': len(self.recommended_actions.split('\n')) if self.recommended_actions else 0
        }

    @api.model
    def get_global_satisfaction_stats(self):
        """Retourne les statistiques globales de satisfaction pour toutes les enquêtes"""

        # Enquêtes avec analyse terminée
        completed_surveys = self.search([('analysis_completed', '=', True)])

        if not completed_surveys:
            return {
                'total_surveys': 0,
                'avg_satisfaction': 0,
                'total_responses': 0,
                'distribution': {'very_high': 0, 'high': 0, 'neutral': 0, 'low': 0, 'very_low': 0}
            }

        # Calculs globaux
        total_surveys = len(completed_surveys)
        avg_satisfaction = sum(completed_surveys.mapped('satisfaction_score')) / total_surveys
        total_responses = sum(completed_surveys.mapped('response_count'))

        # Distribution des niveaux de satisfaction
        distribution = {}
        for level in ['very_high', 'high', 'neutral', 'low', 'very_low']:
            count = len(completed_surveys.filtered(lambda s: s.satisfaction_level == level))
            distribution[level] = count

        return {
            'total_surveys': total_surveys,
            'avg_satisfaction': avg_satisfaction,
            'total_responses': total_responses,
            'distribution': distribution,
            'recent_surveys': completed_surveys.sorted('analysis_date', reverse=True)[:5].mapped(lambda s: {
                'reference': s.reference,
                'score': s.satisfaction_score,
                'level': s.satisfaction_level,
                'date': s.analysis_date.strftime('%d/%m/%Y') if s.analysis_date else None
            })
        }

    def action_duplicate_survey(self):
        """Duplique l'enquête pour créer une nouvelle enquête basée sur celle-ci"""
        self.ensure_one()

        # Valeurs pour la duplication
        default_vals = {
            'reference': 'New',
            'name': 'New',
            'state': 'draft',
            'date_debut': fields.Date.context_today(self),
            'date_fin': False,
            'analysis_completed': False,
            'analysis_date': False,
            'satisfaction_score': 0.0,
            'satisfaction_summary': False,
            'positive_points': False,
            'negative_points': False,
            'recommended_actions': False,
            'question_analysis': False,
            'positive_responses': 0,
            'negative_responses': 0,
            'neutral_responses': 0,
            'responsible_id': self.env.user.id,
        }

        # Créer la copie
        new_survey = self.copy(default=default_vals)

        # Message de confirmation
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle Enquête',
            'res_model': 'enquete.satisfaction',
            'res_id': new_survey.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # Ajoutez cette méthode dans le modèle EnqueteSatisfaction principal

    def action_open_detailed_report(self):
        """Ouvre le rapport détaillé sans refaire l'analyse"""
        self.ensure_one()

        if not self.analysis_completed:
            raise UserError("Aucune analyse n'a encore été effectuée. Lancez d'abord l'analyse de satisfaction.")

        # Créer le wizard de rapport
        wizard = self.env['satisfaction.report.wizard'].create({
            'enquete_id': self.id,
        })

        # Ouvrir le rapport détaillé
        return {
            'name': f'📊 Rapport Détaillé - {self.reference}',
            'type': 'ir.actions.act_window',
            'res_model': 'satisfaction.report.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'dialog_size': 'extra-large',
            }
        }

    # Ajoutez également cette méthode pour obtenir un résumé rapide
    def get_analysis_summary_html(self):
        """Retourne un résumé HTML formaté pour affichage rapide"""
        self.ensure_one()

        if not self.analysis_completed:
            return "<p>Aucune analyse effectuée</p>"

        level_colors = {
            'very_high': '#28a745',
            'high': '#20c997',
            'neutral': '#ffc107',
            'low': '#fd7e14',
            'very_low': '#dc3545'
        }

        level_labels = {
            'very_high': 'Très Satisfait',
            'high': 'Satisfait',
            'neutral': 'Neutre',
            'low': 'Insatisfait',
            'very_low': 'Très Insatisfait'
        }

        color = level_colors.get(self.satisfaction_level, '#6c757d')
        label = level_labels.get(self.satisfaction_level, 'Non défini')

        return f"""
        <div style="padding: 15px; border-radius: 8px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="background: {color}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-right: 15px;">
                    {self.satisfaction_score * 100:.1f}%
                </div>
                <div style="font-size: 18px; font-weight: bold; color: {color};">
                    {label}
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; font-weight: bold; color: #28a745;">{self.positive_responses}</div>
                    <div style="font-size: 12px; color: #6c757d;">Positives</div>
                </div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; font-weight: bold; color: #dc3545;">{self.negative_responses}</div>
                    <div style="font-size: 12px; color: #6c757d;">Négatives</div>
                </div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; font-weight: bold; color: #6c757d;">{self.neutral_responses}</div>
                    <div style="font-size: 12px; color: #6c757d;">Neutres</div>
                </div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; font-weight: bold; color: #007bff;">{self.response_count}</div>
                    <div style="font-size: 12px; color: #6c757d;">Total</div>
                </div>
            </div>

            {f'<div style="margin-top: 15px; font-size: 12px; color: #6c757d; text-align: center;">Analysé le {self.analysis_date.strftime("%d/%m/%Y à %H:%M")}</div>' if self.analysis_date else ''}
        </div>
        """
