from odoo import models, fields, api, _
import openai
import json
import logging
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(name_)


class SupplierAIAnalysis(models.Model):
    _name = 'supplier.ai.analysis'
    _description = 'Analyse IA des fournisseurs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'created_date desc'

    name = fields.Char(string='Nom de l\'analyse', required=True, tracking=True)
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
    risk_score = fields.Float(string='Score de risque IA', help="Score calculé par l'IA (0-10)", tracking=True)
    confidence_level = fields.Float(string='Niveau de confiance', help="Confiance de l'IA (0-100%)", tracking=True)
    key_insights = fields.Html(string='Insights clés', tracking=True)
    recommendations = fields.Html(string='Recommandations IA', tracking=True)
    predicted_trend = fields.Selection([
        ('improving', 'En amélioration'),
        ('stable', 'Stable'),
        ('declining', 'En déclin'),
        ('critical', 'Critique')
    ], string='Tendance prédite', tracking=True)

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
    average_score = fields.Float(string='Score moyen des évaluations', compute='_compute_average_score', store=True)

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
                    # Calculer la moyenne des scores
                    total_score = sum(eval_rec.evaluation_criteria_ids.mapped('score') for eval_rec in evaluations)
                    total_criteria = sum(len(eval_rec.evaluation_criteria_ids) for eval_rec in evaluations)
                    record.average_score = total_score / total_criteria if total_criteria > 0 else 0.0
                else:
                    record.average_score = 0.0
            else:
                record.average_score = 0.0

    @api.model
    def get_openai_client(self):
        """Initialise le client OpenAI"""
        api_key = self.env['ir.config_parameter'].sudo().get_param('openai.api_key')
        if not api_key:
            raise UserError("Clé API OpenAI non configurée. Allez dans Paramètres > Technique > Paramètres système")

        # Configuration pour la nouvelle version d'OpenAI
        import openai
        openai.api_key = api_key
        return openai

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

            # Appeler OpenAI
            client = self.get_openai_client()

            # Utilisation de l'API OpenAI moderne
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Modèle plus accessible
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )

            # Traiter la réponse
            ai_response = response.choices[0].message.content

            try:
                analysis_data = json.loads(ai_response)
            except json.JSONDecodeError:
                # Fallback si la réponse n'est pas en JSON
                analysis_data = {
                    'risk_score': min(max(self.average_score * 2, 0), 10),  # Conversion approximative
                    'confidence_level': 75,
                    'key_insights': ai_response,
                    'recommendations': "Voir les insights pour les recommandations détaillées.",
                    'predicted_trend': 'stable'
                }

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
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else 0,
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
                'phone': supplier.phone or ''
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
        Analysez les données du fournisseur suivant et fournissez une évaluation détaillée:

        Fournisseur: {supplier_data['supplier_info']['name']}
        Nombre d'évaluations: {supplier_data['evaluations_summary']['total_evaluations']}
        Score moyen: {supplier_data['evaluations_summary']['average_score']:.2f}

        Données détaillées: {json.dumps(supplier_data, indent=2, ensure_ascii=False)}
        """

        if self.analysis_type == 'performance_trend':
            return base_prompt + """

            Focus: Analysez les tendances de performance.
            Identifiez les patterns d'amélioration ou de dégradation.
            Prédisez l'évolution future basée sur les données historiques.
            """

        elif self.analysis_type == 'risk_assessment':
            return base_prompt + """

            Focus: Évaluez les risques associés à ce fournisseur.
            Analysez les risques opérationnels, financiers et de qualité.
            Proposez des mesures de mitigation.
            """

        elif self.analysis_type == 'recommendation':
            return base_prompt + """

            Focus: Générez des recommandations stratégiques.
            Proposez des actions concrètes d'amélioration.
            Suggérez des optimisations de la relation fournisseur.
            """

        return base_prompt

    def _get_system_prompt(self):
        """Prompt système pour définir le rôle de l'IA"""
        return """
        Vous êtes un expert en gestion des fournisseurs et en analyse des performances.
        Analysez les données fournies avec expertise et fournissez des insights actionnables.

        Vos réponses doivent être:
        - Précises et factuelles
        - Basées sur les données fournies
        - Orientées action
        - En français
        - Structurées et claires

        Fournissez vos insights sous forme de texte structuré avec:
        1. Analyse de la situation actuelle
        2. Points forts identifiés
        3. Points d'amélioration
        4. Recommandations concrètes
        5. Prédiction de tendance
        """

    def _create_ai_alerts(self, analysis_data):
        """Crée des alertes basées sur l'analyse IA"""
        risk_score = analysis_data.get('risk_score', 0)

        if risk_score > 7:
            # Vérifier si le modèle d'alerte existe
            if self.env.registry.get('supplier.alert'):
                try:
                    self.env['supplier.alert'].create({
                        'name': f'Alerte IA - Risque élevé: {self.fournisseur_id.name}',
                        'fournisseur_id': self.fournisseur_id.id,
                        'alert_type': 'critical',
                        'description': f"L'IA a détecté un risque élevé (score: {risk_score}/10)\n\n"
                                       f"Recommandations: {analysis_data.get('recommendations', '')}",
                        'priority': 'urgent'
                    })
                except Exception as e:
                    _logger.warning(f"Impossible de créer l'alerte: {e}")

    @api.model
    def bulk_analyze_suppliers(self, supplier_ids=None, analysis_type='performance_trend'):
        """Analyse en masse des fournisseurs"""
        if not supplier_ids:
            # Analyser tous les fournisseurs avec des évaluations récentes
            recent_evaluations = self.env['evaluation'].search([
                ('create_date', '>=', datetime.now() - timedelta(days=90)),
                ('state', '=', 'validated')
            ])
            supplier_ids = recent_evaluations.mapped('fournisseur_id.id')

        if not supplier_ids:
            raise UserError("Aucun fournisseur trouvé pour l'analyse.")

        analyses = []
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
                _logger.error(f"Erreur lors de l'analyse du fournisseur {supplier_id}: {e}")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Analyses IA terminées',
            'res_model': 'supplier.ai.analysis',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', analyses)]
        }


class SupplierAIChatbot(models.Model):
    _name = 'supplier.ai.chatbot'
    _description = 'Chatbot IA pour les fournisseurs'

    name = fields.Char(string='Session', required=True, default='Nouvelle session')
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user, readonly=True)
    conversation_history = fields.Html(string='Historique de conversation')
    active_session = fields.Boolean(string='Session active', default=True)
    current_question = fields.Text(string='Question actuelle', help='Posez votre question ici')

    def ask_ai_question(self):
        """Traite la question courante et génère une réponse IA"""
        self.ensure_one()

        if not self.current_question:
            raise UserError("Veuillez saisir une question.")

        question = self.current_question

        try:
            # Préparer le contexte avec les données des fournisseurs
            context = self._prepare_context()

            # Simuler une réponse IA (à remplacer par un vrai appel API)
            ai_response = self._generate_mock_response(question, context)

            # Mettre à jour l'historique
            current_history = self.conversation_history or ''

            new_conversation = f"""
            {current_history}
            <div style="margin: 10px 0; padding: 10px; border-left: 3px solid #007cba;">
                <strong>Vous ({datetime.now().strftime('%H:%M')}):</strong><br/>
                {question}
            </div>
            <div style="margin: 10px 0; padding: 10px; border-left: 3px solid #28a745; background: #f8f9fa;">
                <strong>Assistant IA ({datetime.now().strftime('%H:%M')}):</strong><br/>
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
                    'title': 'Question traitée',
                    'message': 'Votre question a été traitée avec succès.',
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
                    'title': 'Erreur',
                    'message': f'Erreur lors du traitement: {str(e)}',
                    'type': 'danger',
                    'sticky': True
                }
            }

    def _prepare_context(self):
        """Prépare le contexte des données fournisseurs"""
        # Statistiques générales
        total_suppliers = self.env['res.partner'].search_count([('supplier_rank', '>', 0)])
        total_evaluations = self.env['evaluation'].search_count([('state', '=', 'validated')])

        context = {
            'general_stats': {
                'total_suppliers': total_suppliers,
                'total_evaluations': total_evaluations
            },
            'current_date': str(datetime.now().date())
        }

        return context

    def _generate_mock_response(self, question, context):
        """Génère une réponse simulée (à remplacer par un vrai appel IA)"""
        question_lower = question.lower()

        if 'performance' in question_lower or 'performant' in question_lower:
            return f"""
            Basé sur les données disponibles ({context['general_stats']['total_evaluations']} évaluations), 
            voici l'analyse des performances des fournisseurs:

            <ul>
            <li>Les fournisseurs avec les meilleures évaluations maintiennent une moyenne > 4/5</li>
            <li>Les critères les plus importants sont la qualité et les délais</li>
            <li>Recommandation: Focus sur le suivi régulier des KPIs</li>
            </ul>
            """

        elif 'risque' in question_lower:
            return """
            Analyse des risques fournisseurs:

            <ul>
            <li>Risques identifiés: dépendance excessive, qualité variable</li>
            <li>Mitigation: diversification du portefeuille fournisseurs</li>
            <li>Surveillance: mise en place d'alertes automatiques</li>
            </ul>
            """

        else:
            return f"""
            Merci pour votre question. Voici quelques informations générales:

            <ul>
            <li>Nombre total de fournisseurs: {context['general_stats']['total_suppliers']}</li>
            <li>Évaluations disponibles: {context['general_stats']['total_evaluations']}</li>
            <li>Pour des analyses plus détaillées, utilisez les modules d'analyse IA.</li>
            </ul>
            """


# Extension du modèle evaluation pour intégrer l'IA
class EvaluationAIExtended(models.Model):
    _inherit = 'evaluation'

    ai_analysis_ids = fields.One2many('supplier.ai.analysis', 'fournisseur_id',
                                      string='Analyses IA',
                                      domain="[('fournisseur_id', '=', fournisseur_id)]")

    ai_analysis_count = fields.Integer(string='Nombre d\'analyses IA', compute='_compute_ai_analysis_count')

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

        analysis.analyze_supplier_performance()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Analyse IA générée',
            'res_model': 'supplier.ai.analysis',
            'res_id': analysis.id,
            'view_mode': 'form',
            'target': 'new'
        }


# Configuration système pour OpenAI
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    openai_api_key = fields.Char(
        string='Clé API OpenAI',
        config_parameter='openai.api_key',
        help='Votre clé API OpenAI pour les analyses IA'
    )

    openai_model = fields.Selection([
        ('gpt-4-turbo-preview', 'GPT-4 Turbo'),
        ('gpt-4', 'GPT-4'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo')
    ], string='Modèle OpenAI',
        config_parameter='openai.model',
        default='gpt-3.5-turbo',
        help='Modèle OpenAI à utiliser pour les analyses')