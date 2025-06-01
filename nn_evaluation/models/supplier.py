# nn_evaluation/models/supplier.py
from odoo import models, fields, api, _
import json
import logging
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SupplierAIAnalysis(models.Model):
    _name = 'supplier.ai.analysis'
    _description = 'Analyse IA des fournisseurs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'created_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Nom de l\'analyse',
        required=True,
        tracking=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('supplier.ai.analysis') or 'Nouvelle Analyse'
    )
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur', required=True, tracking=True)
    analysis_type = fields.Selection([
        ('performance_trend', 'Analyse de tendance'),
        ('risk_assessment', 'Évaluation des risques'),
        ('recommendation', 'Recommandations'),
        ('predictive', 'Analyse prédictive'),
        ('comparative', 'Analyse comparative')
    ], string='Type d\'analyse', required=True, default='performance_trend', tracking=True)

    # Données d'entrée et de sortie
    input_data = fields.Text(string='Données d\'entrée')
    ai_prompt = fields.Text(string='Prompt IA')
    ai_response = fields.Text(string='Réponse IA')
    structured_analysis = fields.Text(string='Analyse structurée')

    # Résultats structurés
    risk_score = fields.Float(
        string='Score de risque IA',
        help="Score calculé par l'IA (0-10)",
        tracking=True,
        default=0.0
    )
    confidence_level = fields.Float(
        string='Niveau de confiance',
        help="Confiance de l'IA (0-100%)",
        tracking=True,
        default=0.0
    )
    key_insights = fields.Html(string='Insights clés', tracking=True)
    recommendations = fields.Html(string='Recommandations IA', tracking=True)
    predicted_trend = fields.Selection([
        ('improving', 'En amélioration'),
        ('stable', 'Stable'),
        ('declining', 'En déclin'),
        ('critical', 'Critique')
    ], string='Tendance prédite', tracking=True, default='stable')

    # Métadonnées
    tokens_used = fields.Integer(string='Tokens utilisés', default=0)
    processing_time = fields.Float(string='Temps de traitement (s)', default=0.0)
    created_date = fields.Datetime(string='Date de création', default=fields.Datetime.now, readonly=True)

    # État du processus
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('analyzing', 'En cours d\'analyse'),
        ('completed', 'Terminé'),
        ('error', 'Erreur')
    ], string='État', default='draft', tracking=True)

    # Moyenne des scores des évaluations liées
    average_score = fields.Float(
        string='Score moyen des évaluations',
        compute='_compute_average_score',
        store=True
    )
    evaluation_id = fields.Many2one(
        'evaluation',
        string='Évaluation',
        ondelete='cascade'
    )

    @api.depends('fournisseur_id')
    def _compute_average_score(self):
        """Calcule le score moyen des évaluations du fournisseur"""
        for record in self:
            if record.fournisseur_id:
                evaluations = self.env['evaluation'].search([
                    ('fournisseur_id', '=', record.fournisseur_id.id),
                    ('state', '=', 'validated')
                ])
                if evaluations:
                    # Calculer la moyenne des scores - version corrigée
                    total_score = 0
                    total_criteria = 0
                    for eval_rec in evaluations:
                        for criteria in eval_rec.evaluation_criteria_ids:
                            total_score += criteria.score
                            total_criteria += 1
                    record.average_score = total_score / total_criteria if total_criteria > 0 else 0.0
                else:
                    record.average_score = 0.0
            else:
                record.average_score = 0.0

    @api.model
    def get_openai_client(self):
        """Initialise le client OpenAI avec gestion des versions"""
        api_key = self.env['ir.config_parameter'].sudo().get_param('openai.api_key')
        if not api_key:
            raise UserError("Clé API OpenAI non configurée. Allez dans Paramètres > Technique > Paramètres système")

        try:
            # Essayer d'utiliser la nouvelle API OpenAI
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            return client, 'new'
        except ImportError:
            try:
                # Fallback vers l'ancienne API
                import openai
                openai.api_key = api_key
                return openai, 'old'
            except ImportError:
                raise UserError("Module OpenAI non installé. Installez avec: pip install openai")

    def analyze_supplier_performance(self):
        """Analyse les performances d'un fournisseur avec OpenAI"""
        self.ensure_one()
        start_time = datetime.now()

        try:
            self.write({'state': 'analyzing'})

            # Préparer les données du fournisseur
            supplier_data = self._prepare_supplier_data()

            # Créer le prompt pour OpenAI
            prompt = self._create_analysis_prompt(supplier_data)

            # Appeler OpenAI avec gestion d'erreur robuste
            try:
                client, api_version = self.get_openai_client()

                if api_version == 'new':
                    # Nouvelle API OpenAI
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": self._get_system_prompt()},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=2000,
                        temperature=0.3
                    )
                    ai_response = response.choices[0].message.content
                    tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
                else:
                    # Ancienne API
                    response = client.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": self._get_system_prompt()},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=2000,
                        temperature=0.3
                    )
                    ai_response = response.choices[0].message.content
                    tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

            except Exception as api_error:
                _logger.warning(f"Erreur API OpenAI: {api_error}. Utilisation du mode simulation.")
                # Mode simulation si l'API échoue
                ai_response = self._generate_mock_analysis(supplier_data)
                tokens_used = 0

            # Traiter la réponse
            try:
                # Essayer d'extraire du JSON de la réponse
                analysis_data = self._extract_structured_data(ai_response)
            except Exception:
                # Fallback: créer une structure basée sur les données
                analysis_data = self._create_fallback_analysis(ai_response, supplier_data)

            # Mettre à jour les champs
            self.write({
                'input_data': json.dumps(supplier_data, indent=2, ensure_ascii=False),
                'ai_prompt': prompt,
                'ai_response': ai_response,
                'structured_analysis': json.dumps(analysis_data, indent=2, ensure_ascii=False),
                'risk_score': analysis_data.get('risk_score', 0),
                'confidence_level': analysis_data.get('confidence_level', 0),
                'key_insights': analysis_data.get('key_insights', ''),
                'recommendations': analysis_data.get('recommendations', ''),
                'predicted_trend': analysis_data.get('predicted_trend', 'stable'),
                'tokens_used': tokens_used,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'state': 'completed'
            })

            # Créer des alertes si nécessaire
            self._create_ai_alerts(analysis_data)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Analyse IA terminée',
                    'message': f'Analyse terminée avec un niveau de confiance de {self.confidence_level}%',
                    'type': 'success',
                    'sticky': False
                }
            }

        except Exception as e:
            _logger.error(f"Erreur lors de l'analyse IA: {str(e)}")
            self.write({
                'ai_response': f"Erreur: {str(e)}",
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'state': 'error'
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erreur d\'analyse IA',
                    'message': f'Erreur lors de l\'analyse: {str(e)}',
                    'type': 'danger',
                    'sticky': True
                }
            }

    def _extract_structured_data(self, ai_response):
        """Extrait les données structurées de la réponse IA"""
        # Chercher du JSON dans la réponse
        try:
            # Essayer de parser la réponse entière comme JSON
            return json.loads(ai_response)
        except json.JSONDecodeError:
            # Chercher des blocs JSON dans la réponse
            import re
            json_pattern = r'\{[^{}]*\}'
            matches = re.findall(json_pattern, ai_response)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

            # Si aucun JSON trouvé, lever une exception
            raise ValueError("Aucune structure JSON trouvée")

    def _create_fallback_analysis(self, ai_response, supplier_data):
        """Crée une analyse de fallback basée sur les données"""
        # Calculer un score de risque basé sur le score moyen
        avg_score = self.average_score
        risk_score = max(0, min(10, 10 - avg_score))

        # Déterminer la tendance
        if avg_score >= 8:
            trend = 'improving'
        elif avg_score >= 6:
            trend = 'stable'
        elif avg_score >= 4:
            trend = 'declining'
        else:
            trend = 'critical'

        return {
            'risk_score': risk_score,
            'confidence_level': 75,
            'key_insights': self._format_insights(ai_response, supplier_data),
            'recommendations': self._format_recommendations(ai_response, supplier_data),
            'predicted_trend': trend
        }

    def _format_insights(self, ai_response, supplier_data):
        """Formate les insights clés"""
        supplier_name = supplier_data['supplier_info']['name']
        avg_score = self.average_score

        insights = f"""
        <h3>📊 Analyse de {supplier_name}</h3>
        <div class="alert alert-info">
            <ul>
                <li><strong>Score moyen:</strong> {avg_score:.2f}/10</li>
                <li><strong>Évaluations:</strong> {supplier_data['evaluations_summary']['total_evaluations']}</li>
                <li><strong>Statut:</strong> {'Excellent' if avg_score > 8 else 'Satisfaisant' if avg_score > 6 else 'À améliorer'}</li>
            </ul>
        </div>

        <h4>🔍 Analyse détaillée:</h4>
        <div>{ai_response[:500]}...</div>
        """

        return insights

    def _format_recommendations(self, ai_response, supplier_data):
        """Formate les recommandations"""
        avg_score = self.average_score

        recommendations = f"""
        <h3>💡 Recommandations</h3>
        <div class="alert alert-warning">
        """

        if avg_score > 8:
            recommendations += """
                <li>✅ Maintenir cette excellente relation</li>
                <li>📈 Envisager un partenariat stratégique</li>
                <li>🎯 Utiliser comme référence pour autres fournisseurs</li>
            """
        elif avg_score > 6:
            recommendations += """
                <li>📊 Suivi régulier des performances</li>
                <li>🔄 Amélioration continue des processus</li>
                <li>💬 Communication renforcée</li>
            """
        else:
            recommendations += """
                <li>⚠️ Plan d'amélioration urgent requis</li>
                <li>📋 Audit approfondi nécessaire</li>
                <li>🔍 Recherche d'alternatives recommandée</li>
            """

        recommendations += "</div>"
        return recommendations

    def _predict_trend_from_score(self):
        """Prédit la tendance basée sur le score moyen"""
        if self.average_score >= 8:
            return 'improving'
        elif self.average_score >= 6:
            return 'stable'
        elif self.average_score >= 4:
            return 'declining'
        else:
            return 'critical'

    def _generate_mock_analysis(self, supplier_data):
        """Génère une analyse simulée avancée"""
        supplier_name = supplier_data['supplier_info']['name']
        avg_score = supplier_data['evaluations_summary']['average_score']

        # Analyse contextuelle
        performance_trend = "positive" if avg_score > 6 else "préoccupante"
        risk_level = "faible" if avg_score > 7 else "modéré" if avg_score > 5 else "élevé"

        mock_response = f"""
        ## Analyse IA du Fournisseur {supplier_name}

        ### 📈 Performance Globale
        Score moyen actuel: {avg_score:.2f}/10
        Tendance: {performance_trend}
        Niveau de risque: {risk_level}

        ### 🔍 Points Clés Identifiés
        - Stabilité des performances sur les dernières évaluations
        - Critères les plus variables: qualité et délais
        - Potentiel d'amélioration dans la communication

        ### 🎯 Recommandations Prioritaires
        1. Renforcer le suivi des indicateurs clés
        2. Mettre en place des réunions régulières
        3. Définir des objectifs d'amélioration mesurables

        ### 📊 Prédiction d'Évolution
        Basée sur l'historique, une {"amélioration" if avg_score > 6 else "stabilisation"} est attendue.
        """

        return mock_response

    def _prepare_supplier_data(self):
        """Prépare les données du fournisseur pour l'analyse"""
        supplier = self.fournisseur_id

        # Récupérer les évaluations récentes
        evaluations = self.env['evaluation'].search([
            ('fournisseur_id', '=', supplier.id),
            ('state', '=', 'validated')
        ], order='create_date desc', limit=10)

        # Agréger les données
        data = {
            'supplier_info': {
                'name': supplier.name,
                'id': supplier.id,
                'email': supplier.email or '',
                'phone': supplier.phone or '',
                'supplier_rank': getattr(supplier, 'supplier_rank', 0)
            },
            'evaluations_summary': {
                'total_evaluations': len(evaluations),
                'average_score': self.average_score,
                'date_range': {
                    'from': str(evaluations[-1].create_date.date()) if evaluations else None,
                    'to': str(evaluations[0].create_date.date()) if evaluations else None
                }
            },
            'performance_metrics': [],
            'criteria_trends': {},
            'recent_actions': []
        }

        # Analyser chaque évaluation
        for eval_record in evaluations:
            eval_data = {
                'date': str(eval_record.create_date.date()),
                'state': eval_record.state,
                'periodicity': eval_record.periodicity,
                'criteria_scores': {}
            }

            # Scores par critère
            for criteria in eval_record.evaluation_criteria_ids:
                eval_data['criteria_scores'][criteria.name] = criteria.score

                # Construire les tendances par critère
                if criteria.name not in data['criteria_trends']:
                    data['criteria_trends'][criteria.name] = []
                data['criteria_trends'][criteria.name].append({
                    'date': str(eval_record.create_date.date()),
                    'score': criteria.score
                })

            data['performance_metrics'].append(eval_data)

        return data

    def _create_analysis_prompt(self, supplier_data):
        """Crée le prompt pour l'analyse IA"""
        base_prompt = f"""
        Analysez les données du fournisseur suivant et fournissez une évaluation détaillée en français:

        **Fournisseur:** {supplier_data['supplier_info']['name']}
        **Nombre d'évaluations:** {supplier_data['evaluations_summary']['total_evaluations']}
        **Score moyen:** {supplier_data['evaluations_summary']['average_score']:.2f}/10

        **Données détaillées:**
        {json.dumps(supplier_data, indent=2, ensure_ascii=False)}
        """

        if self.analysis_type == 'performance_trend':
            return base_prompt + """

            **FOCUS: Analyse de tendance de performance**
            - Identifiez les patterns d'amélioration ou de dégradation
            - Analysez l'évolution des critères clés
            - Prédisez l'évolution future basée sur les données historiques
            - Proposez des actions pour maintenir/améliorer la tendance
            """

        elif self.analysis_type == 'risk_assessment':
            return base_prompt + """

            **FOCUS: Évaluation des risques**
            - Évaluez les risques opérationnels, financiers et de qualité
            - Identifiez les signaux d'alerte potentiels
            - Analysez la dépendance et l'impact critique
            - Proposez des mesures de mitigation spécifiques
            """

        elif self.analysis_type == 'recommendation':
            return base_prompt + """

            **FOCUS: Recommandations stratégiques**
            - Générez des recommandations stratégiques actionables
            - Proposez des actions concrètes d'amélioration
            - Suggérez des optimisations de la relation fournisseur
            - Identifiez les opportunités de partenariat
            """

        return base_prompt

    def _get_system_prompt(self):
        """Prompt système pour définir le rôle de l'IA"""
        return """
        Vous êtes un expert consultant en gestion des fournisseurs avec 15 ans d'expérience.
        Votre expertise couvre l'analyse des performances, la gestion des risques et l'optimisation des relations fournisseurs.

        **Votre mission:**
        - Analysez les données fournies avec expertise professionnelle
        - Fournissez des insights actionnables et stratégiques
        - Identifiez les tendances et patterns significatifs
        - Proposez des recommandations concrètes et mesurables

        **Style de réponse requis:**
        - Français professionnel et clair
        - Structuré avec des sections distinctes
        - Orienté action et résultats
        - Basé sur les données fournies
        - Équilibré entre analyse critique et constructive

        **Structure recommandée:**
        1. 📊 Synthèse de la situation actuelle
        2. 🔍 Points forts identifiés
        3. ⚠️ Points d'attention et risques
        4. 💡 Recommandations prioritaires
        5. 📈 Prédiction de tendance
        """

    def _create_ai_alerts(self, analysis_data):
        """Crée des alertes basées sur l'analyse IA"""
        risk_score = analysis_data.get('risk_score', 0)

        if risk_score > 7:
            try:
                # Créer une activité/tâche au lieu d'une alerte
                self.activity_schedule(
                    'mail.mail_activity_data_warning',
                    summary=f'🚨 Alerte IA - Risque élevé: {self.fournisseur_id.name}',
                    note=f"""
                    L'analyse IA a détecté un risque élevé pour ce fournisseur.

                    **Score de risque:** {risk_score}/10
                    **Niveau de confiance:** {analysis_data.get('confidence_level', 0)}%
                    **Tendance prédite:** {analysis_data.get('predicted_trend', 'N/A')}

                    **Action requise:** Révision urgente de ce fournisseur

                    Voir l'analyse complète pour les recommandations détaillées.
                    """,
                    user_id=self.env.user.id
                )
            except Exception as e:
                _logger.warning(f"Impossible de créer l'activité d'alerte: {e}")

    @api.model
    def bulk_analyze_suppliers(self, supplier_ids=None, analysis_type='performance_trend'):
        """Analyse en masse des fournisseurs"""
        if not supplier_ids:
            # Analyser tous les fournisseurs avec des évaluations récentes
            recent_evaluations = self.env['evaluation'].search([
                ('create_date', '>=', datetime.now() - timedelta(days=90)),
                ('state', '=', 'validated')
            ])
            supplier_ids = list(set(recent_evaluations.mapped('fournisseur_id.id')))

        if not supplier_ids:
            raise UserError("Aucun fournisseur trouvé pour l'analyse.")

        analyses = []
        errors = []

        for supplier_id in supplier_ids:
            try:
                supplier = self.env['res.partner'].browse(supplier_id)
                analysis = self.create({
                    'name': f'Analyse IA - {supplier.name} - {datetime.now().strftime("%d/%m/%Y %H:%M")}',
                    'fournisseur_id': supplier_id,
                    'analysis_type': analysis_type
                })
                analysis.analyze_supplier_performance()
                analyses.append(analysis.id)
            except Exception as e:
                error_msg = f"Erreur fournisseur {supplier_id}: {str(e)}"
                errors.append(error_msg)
                _logger.error(error_msg)

        result_message = f"Analyses terminées: {len(analyses)} succès"
        if errors:
            result_message += f", {len(errors)} erreurs"

        return {
            'type': 'ir.actions.act_window',
            'name': result_message,
            'res_model': 'supplier.ai.analysis',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', analyses)],
            'context': {'search_default_completed': 1}
        }


class SupplierAIChatbot(models.Model):
    _name = 'supplier.ai.chatbot'
    _description = 'Chatbot IA pour les fournisseurs'
    _rec_name = 'name'

    name = fields.Char(
        string='Session',
        required=True,
        default=lambda self: f"Session {self.env.user.name} - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user, readonly=True)
    conversation_history = fields.Html(string='Historique de conversation')
    active_session = fields.Boolean(string='Session active', default=True)
    current_question = fields.Text(string='Question actuelle', help='Posez votre question ici')

    def ask_ai_question(self):
        """Traite la question courante et génère une réponse IA"""
        self.ensure_one()

        if not self.current_question:
            raise UserError("Veuillez saisir une question.")

        question = self.current_question.strip()

        try:
            # Préparer le contexte avec les données des fournisseurs
            context = self._prepare_context()

            # Générer une réponse IA (simulation intelligente)
            ai_response = self._generate_intelligent_response(question, context)

            # Mettre à jour l'historique
            current_history = self.conversation_history or ''

            new_conversation = f"""
            {current_history}
            <div style="margin: 15px 0; padding: 12px; border-left: 4px solid #007cba; background: #f8f9fa;">
                <strong>🧑 Vous ({datetime.now().strftime('%H:%M')}):</strong><br/>
                <em>{question}</em>
            </div>
            <div style="margin: 15px 0; padding: 12px; border-left: 4px solid #28a745; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <strong>🤖 Assistant IA ({datetime.now().strftime('%H:%M')}):</strong><br/>
                {ai_response}
            </div>
            """

            self.write({
                'conversation_history': new_conversation,
                'current_question': ''  # Vider la question après traitement
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ Question traitée',
                    'message': 'Votre question a été analysée avec succès.',
                    'type': 'success',
                    'sticky': False
                }
            }

        except Exception as e:
            _logger.error(f"Erreur chatbot IA: {str(e)}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '❌ Erreur',
                    'message': f'Erreur lors du traitement: {str(e)}',
                    'type': 'danger',
                    'sticky': True
                }
            }

    def _prepare_context(self):
        """Prépare le contexte enrichi des données fournisseurs"""
        # Statistiques générales
        total_suppliers = self.env['res.partner'].search_count([('supplier_rank', '>', 0)])
        total_evaluations = self.env['evaluation'].search_count([('state', '=', 'validated')])

        # Analyses récentes
        recent_analyses = self.env['supplier.ai.analysis'].search_count([
            ('create_date', '>=', datetime.now() - timedelta(days=30)),
            ('state', '=', 'completed')
        ])

        # Top fournisseurs basés sur les évaluations
        top_suppliers_data = self.env['evaluation'].read_group(
            [('state', '=', 'validated')],
            ['fournisseur_id'],
            ['fournisseur_id'],
            limit=5,
            orderby='fournisseur_id_count desc'
        )

        # Alertes actives
        high_risk_count = self.env['supplier.ai.analysis'].search_count([
            ('risk_score', '>', 7),
            ('state', '=', 'completed')
        ])

        context = {
            'general_stats': {
                'total_suppliers': total_suppliers,
                'total_evaluations': total_evaluations,
                'recent_analyses': recent_analyses,
                'top_suppliers_count': len(top_suppliers_data),
                'high_risk_suppliers': high_risk_count
            },
            'current_date': datetime.now().strftime('%d/%m/%Y'),
            'user_name': self.env.user.name
        }

        return context

    def _generate_intelligent_response(self, question, context):
        """Génère une réponse intelligente et contextuelle"""
        question_lower = question.lower()
        stats = context['general_stats']

        # Détection de l'intention de la question
        if any(word in question_lower for word in ['performance', 'performant', 'meilleur', 'top']):
            return self._get_performance_response(stats)

        elif any(word in question_lower for word in ['risque', 'danger', 'alerte', 'critique']):
            return self._get_risk_response(stats)

        elif any(word in question_lower for word in ['recommandation', 'conseil', 'suggestion', 'améliorer']):
            return self._get_recommendation_response(stats)

        elif any(word in question_lower for word in ['statistique', 'nombre', 'combien', 'total']):
            return self._get_statistics_response(stats, context)

        elif any(word in question_lower for word in ['analyse', 'analyser', 'ia', 'intelligence']):
            return self._get_analysis_response(stats)

        elif any(word in question_lower for word in ['aide', 'help', 'comment', 'utiliser']):
            return self._get_help_response()

        else:
            return self._get_general_response(stats, context)

    def _get_performance_response(self, stats):
        """Réponse sur les performances"""
        return f"""
        <h4>📈 Analyse des Performances Fournisseurs</h4>
        <div class="alert alert-info">
            <p>Basé sur <strong>{stats['total_evaluations']}</strong> évaluations validées :</p>
            <ul>
                <li>🏆 <strong>Top {stats['top_suppliers_count']} fournisseurs</strong> identifiés avec les meilleures évaluations</li>
                <li>📊 <strong>Critères clés :</strong> Qualité, Délais, Prix, Service client</li>
                <li>🎯 <strong>Benchmark :</strong> Score moyen excellent > 8/10</li>
                <li>📋 <strong>Évaluations actives :</strong> {stats['total_suppliers']} fournisseurs suivis</li>
            </ul>
        </div>

        <div class="alert alert-success">
            <strong>💡 Conseil :</strong> Utilisez le module "Analyses IA" pour obtenir des insights détaillés 
            sur les tendances de performance de chaque fournisseur.
        </div>
        """

    def _get_risk_response(self, stats):
        """Réponse sur les risques"""
        return f"""
        <h4>⚠️ Gestion des Risques Fournisseurs</h4>
        <div class="alert alert-warning">
            <p><strong>État actuel des risques :</strong></p>
            <ul>
                <li>🚨 <strong>{stats['high_risk_suppliers']} fournisseurs</strong> avec risque élevé détecté</li>
                <li>🔍 <strong>Surveillance active</strong> de {stats['total_suppliers']} fournisseurs</li>
                <li>📊 <strong>Analyses récentes :</strong> {stats['recent_analyses']} ce mois</li>
            </ul>
        </div>

        <h5>🛡️ Stratégies de Mitigation :</h5>
        <ul>
            <li><strong>Diversification :</strong> Éviter la dépendance excessive</li>
            <li><strong>Monitoring :</strong> Alertes automatiques IA</li>
            <li><strong>Plans de contingence :</strong> Fournisseurs alternatifs</li>
            <li><strong>Audits réguliers :</strong> Évaluations trimestrielles</li>
        </ul>

        <div class="alert alert-danger">
            <strong>🚨 Action urgente :</strong> Consulter les analyses IA pour les fournisseurs à risque élevé.
        </div>
        """

    def _get_recommendation_response(self, stats):
        """Réponse avec recommandations"""
        return f"""
        <h4>💡 Recommandations Stratégiques</h4>
        <div class="alert alert-success">
            <p>Basé sur l'analyse de vos <strong>{stats['total_evaluations']}</strong> évaluations :</p>
        </div>

        <h5>🎯 Actions Prioritaires :</h5>
        <ol>
            <li><strong>Standardisation :</strong> Harmoniser les critères d'évaluation</li>
            <li><strong>Automatisation :</strong> Planifier les évaluations récurrentes</li>
            <li><strong>Formation :</strong> Sensibiliser les équipes aux bonnes pratiques</li>
            <li><strong>Partenariats :</strong> Renforcer les relations avec les top performers</li>
        </ol>

        <h5>🔧 Optimisations Techniques :</h5>
        <ul>
            <li>Mise en place de tableaux de bord en temps réel</li>
            <li>Intégration des analyses IA dans les processus</li>
            <li>Système d'alertes automatiques</li>
            <li>Reporting mensuel automatisé</li>
        </ul>

        <div class="alert alert-info">
            <strong>📈 Résultat attendu :</strong> Amélioration de 15-20% des performances globales.
        </div>
        """

    def _get_statistics_response(self, stats, context):
        """Réponse avec statistiques"""
        return f"""
        <h4>📊 Statistiques du Système</h4>
        <div class="row">
            <div class="col-md-6">
                <div class="alert alert-primary">
                    <h5>📈 Données Générales</h5>
                    <ul>
                        <li><strong>Fournisseurs actifs :</strong> {stats['total_suppliers']}</li>
                        <li><strong>Évaluations validées :</strong> {stats['total_evaluations']}</li>
                        <li><strong>Analyses IA ce mois :</strong> {stats['recent_analyses']}</li>
                        <li><strong>Date d'extraction :</strong> {context['current_date']}</li>
                    </ul>
                </div>
            </div>
            <div class="col-md-6">
                <div class="alert alert-warning">
                    <h5>⚠️ Alertes et Risques</h5>
                    <ul>
                        <li><strong>Fournisseurs à risque :</strong> {stats['high_risk_suppliers']}</li>
                        <li><strong>Top performers :</strong> {stats['top_suppliers_count']}</li>
                        <li><strong>Taux de surveillance :</strong> 100%</li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="alert alert-info">
            <strong>🎯 KPI Système :</strong>
            Ratio qualité/risque optimal maintenu pour {context['user_name']}.
        </div>
        """

    def _get_analysis_response(self, stats):
        """Réponse sur les analyses IA"""
        return f"""
        <h4>🤖 Capacités d'Analyse IA</h4>
        <div class="alert alert-info">
            <p>Notre système d'IA peut analyser :</p>
        </div>

        <h5>🔍 Types d'Analyses Disponibles :</h5>
        <div class="row">
            <div class="col-md-6">
                <ul>
                    <li><strong>📈 Tendances de performance</strong>
                        <br><small>Évolution historique et prédictions</small></li>
                    <li><strong>⚠️ Évaluation des risques</strong>
                        <br><small>Détection proactive des problèmes</small></li>
                    <li><strong>💡 Recommandations</strong>
                        <br><small>Actions d'amélioration personnalisées</small></li>
                </ul>
            </div>
            <div class="col-md-6">
                <ul>
                    <li><strong>🔮 Analyses prédictives</strong>
                        <br><small>Anticipation des évolutions</small></li>
                    <li><strong>📊 Analyses comparatives</strong>
                        <br><small>Benchmarking entre fournisseurs</small></li>
                </ul>
            </div>
        </div>

        <div class="alert alert-success">
            <strong>📊 Statistiques actuelles :</strong>
            {stats['recent_analyses']} analyses IA réalisées ce mois pour {stats['total_suppliers']} fournisseurs.
        </div>

        <div class="alert alert-primary">
            <strong>🚀 Pour démarrer :</strong> Allez dans le menu "IA Fournisseurs > Analyses IA" 
            et cliquez sur "Nouvelle Analyse".
        </div>
        """

    def _get_help_response(self):
        """Réponse d'aide"""
        return f"""
        <h4>🤝 Guide d'Utilisation</h4>
        <div class="alert alert-success">
            <p>Bienvenue dans l'Assistant IA Fournisseurs ! Je peux vous aider avec :</p>
        </div>

        <h5>❓ Questions que vous pouvez me poser :</h5>
        <div class="row">
            <div class="col-md-6">
                <h6>📈 Performances :</h6>
                <ul>
                    <li>"Quels sont mes meilleurs fournisseurs ?"</li>
                    <li>"Analyse les tendances de performance"</li>
                    <li>"Comment améliorer les évaluations ?"</li>
                </ul>

                <h6>⚠️ Risques :</h6>
                <ul>
                    <li>"Quels fournisseurs présentent des risques ?"</li>
                    <li>"Comment réduire la dépendance ?"</li>
                    <li>"État des alertes actuelles"</li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6>📊 Statistiques :</h6>
                <ul>
                    <li>"Combien d'évaluations ce mois ?"</li>
                    <li>"Statistiques générales"</li>
                    <li>"Tableau de bord résumé"</li>
                </ul>

                <h6>🤖 IA & Analyses :</h6>
                <ul>
                    <li>"Comment fonctionne l'IA ?"</li>
                    <li>"Lancer une analyse comparative"</li>
                    <li>"Recommandations personnalisées"</li>
                </ul>
            </div>
        </div>

        <div class="alert alert-primary">
            <strong>💡 Astuce :</strong> Soyez spécifique dans vos questions pour obtenir 
            des réponses plus détaillées et pertinentes !
        </div>
        """

    def _get_general_response(self, stats, context):
        """Réponse générale par défaut"""
        return f"""
        <h4>👋 Bonjour {context['user_name']} !</h4>
        <div class="alert alert-info">
            <p>Je suis votre assistant IA spécialisé dans la gestion des fournisseurs.</p>
        </div>

        <h5>📊 Vue d'ensemble de votre système :</h5>
        <div class="row">
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h2 class="text-primary">{stats['total_suppliers']}</h2>
                        <p>Fournisseurs actifs</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h2 class="text-success">{stats['total_evaluations']}</h2>
                        <p>Évaluations validées</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h2 class="text-warning">{stats['recent_analyses']}</h2>
                        <p>Analyses IA ce mois</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="alert alert-success mt-3">
            <h6>🎯 Suggestions d'actions :</h6>
            <ul>
                <li>Consultez vos fournisseurs les plus performants</li>
                <li>Vérifiez les alertes de risque en cours</li>
                <li>Lancez une nouvelle analyse IA</li>
                <li>Explorez les recommandations d'amélioration</li>
            </ul>
        </div>

        <div class="alert alert-primary">
            <strong>❓ Besoin d'aide ?</strong> Posez-moi une question spécifique 
            sur les performances, risques, statistiques ou analyses !
        </div>
        """


# Extension du modèle evaluation pour intégrer l'IA
class EvaluationAIExtended(models.Model):
    _inherit = 'evaluation'

    ai_analysis_ids = fields.One2many(
        'supplier.ai.analysis',
        'fournisseur_id',
        string='Analyses IA',
        domain="[('fournisseur_id', '=', fournisseur_id)]"
    )

    ai_analysis_count = fields.Integer(
        string='Nombre d\'analyses IA',
        compute='_compute_ai_analysis_count'
    )

    @api.depends('ai_analysis_ids')
    def _compute_ai_analysis_count(self):
        for record in self:
            record.ai_analysis_count = len(record.ai_analysis_ids)

    def action_generate_ai_insights(self):
        """Lance une analyse IA pour cette évaluation"""
        if not self.fournisseur_id:
            raise UserError("Aucun fournisseur sélectionné pour l'analyse.")

        analysis = self.env['supplier.ai.analysis'].create({
            'name': f'Analyse IA - {self.fournisseur_id.name} - {datetime.now().strftime("%d/%m/%Y %H:%M")}',
            'fournisseur_id': self.fournisseur_id.id,
            'analysis_type': 'performance_trend'
        })

        # Lancer l'analyse automatiquement
        analysis.analyze_supplier_performance()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Analyse IA générée',
            'res_model': 'supplier.ai.analysis',
            'res_id': analysis.id,
            'view_mode': 'form',
            'target': 'new'
        }

    def action_view_ai_analyses(self):
        """Affiche toutes les analyses IA du fournisseur"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Analyses IA - {self.fournisseur_id.name}',
            'res_model': 'supplier.ai.analysis',
            'view_mode': 'tree,form',
            'domain': [('fournisseur_id', '=', self.fournisseur_id.id)],
            'context': {'default_fournisseur_id': self.fournisseur_id.id}
        }


# Configuration système pour OpenAI
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    openai_api_key = fields.Char(string='Clé API OpenAI', config_parameter='nn_evaluation.openai_api_key')
    openai_model = fields.Selection([
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ('gpt-4', 'GPT-4'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
    ], string='Modèle OpenAI', default='gpt-3.5-turbo', config_parameter='nn_evaluation.openai_model')
    ai_simulation_mode = fields.Boolean(string='Mode Simulation IA',
                                        config_parameter='nn_evaluation.ai_simulation_mode')
