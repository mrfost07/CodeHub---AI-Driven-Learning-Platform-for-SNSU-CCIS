import uuid
import json
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone


class ProjectMentorSession(models.Model):
    """
    Model representing AI Project Mentor sessions specifically for SNSU CCIS students.
    Provides code review, bug detection, project guidance, and personalized learning recommendations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mentor_sessions',
        verbose_name=_('user')
    )
    
    # Project context
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='mentor_sessions',
        verbose_name=_('project')
    )
    
    # Session type and focus
    session_type = models.CharField(
        _('session type'),
        max_length=30,
        choices=[
            ('code_review', 'Code Review'),
            ('bug_detection', 'Bug Detection'),
            ('project_guidance', 'Project Guidance'),
            ('documentation_help', 'Documentation Help'),
            ('learning_recommendation', 'Learning Recommendation'),
        ],
        default='project_guidance'
    )
    
    # Session content
    code_snippet = models.TextField(_('code snippet'), blank=True)
    user_question = models.TextField(_('user question'))
    ai_response = models.TextField(_('AI response'))
    
    # Learning recommendations
    learning_resources = models.ManyToManyField(
        'learning.LearningModule',
        blank=True,
        related_name='recommended_in_sessions',
        verbose_name=_('recommended learning resources')
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('project mentor session')
        verbose_name_plural = _('project mentor sessions')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Mentor Session: {self.session_type} for {self.project.name}"

    # Session status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('archived', 'Archived'),
        ],
        default='active'
    )

    # Session metadata
    total_messages = models.IntegerField(_('total messages'), default=0)
    ai_model_used = models.CharField(_('AI model'), max_length=50, default='gpt-4')
    tokens_used = models.IntegerField(_('tokens used'), default=0)
    cost_estimate = models.DecimalField(
        _('cost estimate'),
        max_digits=8,
        decimal_places=4,
        default=0,
        validators=[MinValueValidator(0)]
    )

    # Session settings
    temperature = models.DecimalField(
        _('temperature'),
        max_digits=3,
        decimal_places=2,
        default=0.7,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text=_('Controls randomness in AI responses (0-2)')
    )
    max_tokens = models.IntegerField(
        _('max tokens per response'),
        default=2000,
        validators=[MinValueValidator(100), MaxValueValidator(4000)]
    )

    # User feedback and rating
    user_rating = models.IntegerField(
        _('user rating'),
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('User satisfaction rating (1-5)')
    )
    feedback_text = models.TextField(_('feedback'), blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    last_activity = models.DateTimeField(_('last activity'), auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)

    class Meta:
        verbose_name = _('AI chat session')
        verbose_name_plural = _('AI chat sessions')
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.user.email} - {self.title or self.session_type}"

    def get_conversation_length(self):
        """Get the number of messages in this session"""
        return self.messages.count()

    def get_total_cost(self):
        """Calculate total estimated cost for this session"""
        # This would depend on your OpenAI pricing
        # For now, return the stored estimate
        return self.cost_estimate

    def add_message(self, role, content, metadata=None):
        """Add a message to this session"""
        message = AIMessage.objects.create(
            session=self,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.total_messages += 1
        self.last_activity = models.timezone.now()
        self.save()
        return message

    def complete_session(self):
        """Mark session as completed"""
        self.status = 'completed'
        self.completed_at = models.timezone.now()
        self.save()

    def archive_session(self):
        """Archive the session"""
        self.status = 'archived'
        self.save()


class AIMessage(models.Model):
    """
    Model representing individual messages in AI chat sessions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ProjectMentorSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('session')
    )

    # Message content
    role = models.CharField(
        _('message role'),
        max_length=20,
        choices=[
            ('user', 'User'),
            ('assistant', 'AI Assistant'),
            ('system', 'System'),
        ]
    )
    content = models.TextField(_('message content'))

    # Message metadata
    metadata = models.JSONField(_('metadata'), default=dict, help_text=_('Additional message data'))
    tokens_used = models.IntegerField(_('tokens used'), default=0)
    processing_time = models.DecimalField(
        _('processing time (seconds)'),
        max_digits=6,
        decimal_places=3,
        blank=True,
        null=True
    )

    # Code-related metadata
    contains_code = models.BooleanField(_('contains code'), default=False)
    code_language = models.CharField(_('code language'), max_length=30, blank=True)
    code_snippet = models.TextField(_('code snippet'), blank=True)

    # Message timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('AI message')
        verbose_name_plural = _('AI messages')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

    def extract_code_snippets(self):
        """Extract code snippets from message content"""
        # This would use a code detection library in practice
        # For now, return stored code snippet if any
        return self.code_snippet if self.code_snippet else None

    def get_formatted_content(self):
        """Get content formatted for display"""
        return self.content


class CodeAnalysis(models.Model):
    """
    Model representing AI-powered code analysis results for bugs,
    performance, security, and best practices.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ProjectMentorSession,
        on_delete=models.CASCADE,
        related_name='code_analyses',
        verbose_name=_('session')
    )

    # Analysis target
    code_snippet = models.TextField(_('code snippet'))
    programming_language = models.CharField(_('programming language'), max_length=30)
    file_name = models.CharField(_('file name'), max_length=255, blank=True)

    # Analysis configuration
    analysis_type = models.CharField(
        _('analysis type'),
        max_length=30,
        choices=[
            ('bug_detection', 'Bug Detection'),
            ('performance', 'Performance Analysis'),
            ('security', 'Security Audit'),
            ('best_practices', 'Best Practices'),
            ('complexity', 'Complexity Analysis'),
            ('comprehensive', 'Comprehensive Review'),
        ]
    )

    # Analysis results
    findings = models.JSONField(_('findings'), default=list)
    recommendations = models.JSONField(_('recommendations'), default=list)
    severity_score = models.IntegerField(
        _('severity score'),
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_('Overall severity (1-10)')
    )

    # Analysis metadata
    ai_model_used = models.CharField(_('AI model'), max_length=50, default='gpt-4')
    tokens_used = models.IntegerField(_('tokens used'), default=0)
    processing_time = models.DecimalField(
        _('processing time (seconds)'),
        max_digits=6,
        decimal_places=3,
        blank=True,
        null=True
    )

    # Analysis status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)

    class Meta:
        verbose_name = _('code analysis')
        verbose_name_plural = _('code analyses')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.analysis_type} - {self.file_name or 'Unknown file'}"

    def get_issues_count(self):
        """Get count of issues found"""
        return len(self.findings)

    def get_critical_issues(self):
        """Get critical severity issues"""
        return [f for f in self.findings if f.get('severity') == 'critical']

    def get_formatted_findings(self):
        """Get findings formatted for display"""
        return self.findings


class LearningRecommendation(models.Model):
    """
    Model representing personalized learning recommendations
    generated by AI based on user progress and goals.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_recommendations',
        verbose_name=_('user')
    )
    session = models.ForeignKey(
        ProjectMentorSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendations',
        verbose_name=_('session')
    )

    # Recommendation details
    recommendation_type = models.CharField(
        _('recommendation type'),
        max_length=30,
        choices=[
            ('career_path', 'Career Path'),
            ('learning_module', 'Learning Module'),
            ('skill_development', 'Skill Development'),
            ('project_idea', 'Project Idea'),
            ('certification', 'Certification'),
            ('resource', 'Learning Resource'),
        ]
    )

    # Recommended content
    title = models.CharField(_('recommendation title'), max_length=200)
    description = models.TextField(_('description'))
    reason = models.TextField(_('reason for recommendation'), help_text=_('Why this was recommended'))

    # Target content (optional)
    recommended_career_path = models.ForeignKey(
        'learning.CareerPath',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendations',
        verbose_name=_('recommended career path')
    )
    recommended_module = models.ForeignKey(
        'learning.LearningModule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendations',
        verbose_name=_('recommended module')
    )
    recommended_skill = models.ForeignKey(
        'accounts.Skill',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendations',
        verbose_name=_('recommended skill')
    )

    # External resources
    external_url = models.URLField(_('external URL'), blank=True)
    resource_type = models.CharField(
        _('resource type'),
        max_length=30,
        choices=[
            ('documentation', 'Documentation'),
            ('tutorial', 'Tutorial'),
            ('course', 'Online Course'),
            ('book', 'Book'),
            ('video', 'Video'),
            ('practice', 'Practice Platform'),
            ('tool', 'Tool/Software'),
        ],
        blank=True
    )

    # Recommendation metadata
    confidence_score = models.DecimalField(
        _('confidence score'),
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text=_('AI confidence in this recommendation (0-1)')
    )
    priority_score = models.IntegerField(
        _('priority score'),
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_('Recommendation priority (1-10)')
    )

    # User interaction
    is_viewed = models.BooleanField(_('viewed'), default=False)
    is_dismissed = models.BooleanField(_('dismissed'), default=False)
    user_rating = models.IntegerField(
        _('user rating'),
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    viewed_at = models.DateTimeField(_('viewed at'), blank=True, null=True)
    expires_at = models.DateTimeField(_('expires at'), blank=True, null=True)

    class Meta:
        verbose_name = _('learning recommendation')
        verbose_name_plural = _('learning recommendations')
        ordering = ['-priority_score', '-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    def mark_viewed(self):
        """Mark recommendation as viewed"""
        self.is_viewed = True
        self.viewed_at = models.timezone.now()
        self.save()

    def dismiss(self):
        """Dismiss this recommendation"""
        self.is_dismissed = True
        self.save()

    def rate(self, rating):
        """Rate this recommendation"""
        self.user_rating = rating
        self.save()


class ProjectGuidance(models.Model):
    """
    Model representing AI-generated project guidance and architecture advice.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ProjectMentorSession,
        on_delete=models.CASCADE,
        related_name='project_guidance',
        verbose_name=_('session')
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='ai_guidance',
        verbose_name=_('project')
    )

    # Guidance details
    guidance_type = models.CharField(
        _('guidance type'),
        max_length=30,
        choices=[
            ('architecture', 'Architecture Design'),
            ('technology_stack', 'Technology Stack'),
            ('project_structure', 'Project Structure'),
            ('best_practices', 'Best Practices'),
            ('optimization', 'Performance Optimization'),
            ('security', 'Security Guidelines'),
            ('deployment', 'Deployment Strategy'),
        ]
    )

    # Content
    title = models.CharField(_('guidance title'), max_length=200)
    content = models.TextField(_('guidance content'))
    recommendations = models.JSONField(_('recommendations'), default=list)

    # Implementation details
    implementation_steps = models.JSONField(_('implementation steps'), default=list)
    estimated_effort = models.CharField(
        _('estimated effort'),
        max_length=20,
        choices=[
            ('low', 'Low (1-2 hours)'),
            ('medium', 'Medium (3-8 hours)'),
            ('high', 'High (1-3 days)'),
            ('very_high', 'Very High (1+ weeks)'),
        ],
        default='medium'
    )

    # Metadata
    complexity_level = models.CharField(
        _('complexity level'),
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='intermediate'
    )

    # User interaction
    is_implemented = models.BooleanField(_('implemented'), default=False)
    user_feedback = models.TextField(_('user feedback'), blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    implemented_at = models.DateTimeField(_('implemented at'), blank=True, null=True)

    class Meta:
        verbose_name = _('project guidance')
        verbose_name_plural = _('project guidance')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.title}"

    def mark_implemented(self):
        """Mark guidance as implemented"""
        self.is_implemented = True
        self.implemented_at = models.timezone.now()
        self.save()


class AIMentorProfile(models.Model):
    """
    Model representing AI mentor configuration and user preferences.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_mentor_profile',
        verbose_name=_('user')
    )

    # AI preferences
    preferred_ai_model = models.CharField(
        _('preferred AI model'),
        max_length=50,
        choices=[
            ('gpt-4', 'GPT-4'),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ],
        default='gpt-4'
    )
    preferred_temperature = models.DecimalField(
        _('preferred temperature'),
        max_digits=3,
        decimal_places=2,
        default=0.7,
        validators=[MinValueValidator(0), MaxValueValidator(2)]
    )

    # Learning preferences
    learning_goals = models.ManyToManyField(
        'accounts.CareerInterest',
        related_name='ai_mentor_profiles',
        verbose_name=_('learning goals'),
        blank=True
    )
    preferred_difficulty = models.CharField(
        _('preferred difficulty'),
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('mixed', 'Mixed'),
        ],
        default='intermediate'
    )

    # Communication preferences
    communication_style = models.CharField(
        _('communication style'),
        max_length=20,
        choices=[
            ('formal', 'Formal'),
            ('casual', 'Casual'),
            ('technical', 'Technical'),
            ('mentor_like', 'Mentor-like'),
        ],
        default='mentor_like'
    )
    code_explanation_level = models.CharField(
        _('code explanation level'),
        max_length=20,
        choices=[
            ('simple', 'Simple'),
            ('detailed', 'Detailed'),
            ('expert', 'Expert'),
        ],
        default='detailed'
    )

    # Feature preferences
    enable_code_analysis = models.BooleanField(_('enable code analysis'), default=True)
    enable_learning_recommendations = models.BooleanField(_('enable learning recommendations'), default=True)
    enable_project_guidance = models.BooleanField(_('enable project guidance'), default=True)

    # Usage limits and safety
    daily_message_limit = models.IntegerField(
        _('daily message limit'),
        default=50,
        validators=[MinValueValidator(10), MaxValueValidator(200)]
    )
    messages_today = models.IntegerField(_('messages today'), default=0)
    last_reset_date = models.DateField(_('last reset date'), auto_now=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('AI mentor profile')
        verbose_name_plural = _('AI mentor profiles')

    def __str__(self):
        return f"AI Mentor Profile - {self.user.email}"

    def can_send_message(self):
        """Check if user can send more messages today"""
        today = models.timezone.now().date()
        if self.last_reset_date != today:
            self.messages_today = 0
            self.last_reset_date = today
            self.save()

        return self.messages_today < self.daily_message_limit

    def increment_message_count(self):
        """Increment daily message count"""
        self.messages_today += 1
        self.save()

    def reset_daily_limit(self):
        """Reset daily message limit"""
        self.messages_today = 0
        self.last_reset_date = models.timezone.now().date()
        self.save()
