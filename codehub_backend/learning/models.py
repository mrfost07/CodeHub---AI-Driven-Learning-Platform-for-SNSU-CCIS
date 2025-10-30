import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class CareerPath(models.Model):
    """
    Model representing academic career paths for IT/CS/IS programs
    with difficulty levels and module progression.
    Specifically designed for SNSU CCIS students.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('career path name'), max_length=100, unique=True)
    slug = models.SlugField(_('slug'), max_length=100, unique=True)
    description = models.TextField(_('description'))
    program_type = models.CharField(
        _('program type'),
        max_length=20,
        choices=[
            ('bsit', 'Bachelor of Science in Information Technology'),
            ('bscs', 'Bachelor of Science in Computer Science'),
            ('bsis', 'Bachelor of Science in Information Systems'),
        ]
    )
    snsu_ccis_specific = models.BooleanField(_('SNSU CCIS specific'), default=True)
    difficulty_level = models.CharField(
        _('difficulty level'),
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='beginner'
    )
    estimated_duration = models.IntegerField(
        _('estimated duration (weeks)'),
        validators=[MinValueValidator(1), MaxValueValidator(52)]
    )
    total_modules = models.IntegerField(_('total modules'), validators=[MinValueValidator(1)])
    points_reward = models.IntegerField(_('points reward'), default=100, validators=[MinValueValidator(0)])

    # Prerequisites and requirements
    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='leads_to',
        help_text=_('Career paths that must be completed before this one')
    )
    required_skills = models.ManyToManyField(
        'accounts.Skill',
        blank=True,
        related_name='required_for_paths',
        help_text=_('Skills required to start this career path')
    )

    # Visual and metadata
    icon = models.CharField(_('icon class'), max_length=50, help_text=_('CSS icon class or emoji'))
    color = models.CharField(_('color code'), max_length=7, default='#007bff', help_text=_('Hex color code'))
    is_active = models.BooleanField(_('active'), default=True)
    is_featured = models.BooleanField(_('featured'), default=False)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('career path')
        verbose_name_plural = _('career paths')
        ordering = ['program_type', 'difficulty_level', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_program_type_display()})"

    def get_completion_rate(self):
        """Calculate completion rate based on enrolled users"""
        total_enrolled = self.user_progress.count()
        if total_enrolled == 0:
            return 0
        completed = self.user_progress.filter(is_completed=True).count()
        return (completed / total_enrolled) * 100

    def get_average_rating(self):
        """Get average rating from user reviews"""
        ratings = self.reviews.filter(is_active=True)
        if not ratings:
            return 0
        return sum(review.rating for review in ratings) / len(ratings)


class LearningModule(models.Model):
    """
    Model representing individual learning modules within career paths
    with various content types and assessments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    career_path = models.ForeignKey(
        CareerPath,
        on_delete=models.CASCADE,
        related_name='modules',
        verbose_name=_('career path')
    )
    is_snsu_ccis_specific = models.BooleanField(_('SNSU CCIS specific'), default=False, 
                                              help_text=_('Indicates if this module is specific to SNSU CCIS curriculum'))
    title = models.CharField(_('module title'), max_length=200)
    slug = models.SlugField(_('slug'), max_length=200)
    description = models.TextField(_('description'))
    module_number = models.IntegerField(_('module number'), validators=[MinValueValidator(1)])

    # Content configuration
    content_type = models.CharField(
        _('content type'),
        max_length=20,
        choices=[
            ('video', 'Video Content'),
            ('text', 'Text Content'),
            ('interactive', 'Interactive Content'),
            ('mixed', 'Mixed Content'),
        ]
    )

    # Media content
    video_url = models.URLField(_('video URL'), blank=True, help_text=_('YouTube, Vimeo, or direct video URL'))
    video_duration = models.IntegerField(_('video duration (minutes)'), blank=True, null=True)
    content_text = models.TextField(_('content text'), blank=True)
    attachments = models.FileField(_('attachments'), upload_to='module_attachments/', blank=True)

    # Learning objectives and outcomes
    learning_objectives = models.TextField(_('learning objectives'), help_text=_('What students will learn'))
    key_takeaways = models.TextField(_('key takeaways'), blank=True, help_text=_('Main points to remember'))

    # Difficulty and progression
    difficulty_level = models.CharField(
        _('difficulty level'),
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='beginner'
    )
    estimated_time = models.IntegerField(
        _('estimated time (minutes)'),
        validators=[MinValueValidator(5), MaxValueValidator(480)]
    )

    # Module relationships
    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='leads_to_modules',
        help_text=_('Modules that must be completed before this one')
    )

    # Assessment and quiz
    has_quiz = models.BooleanField(_('has quiz'), default=True)
    passing_score = models.IntegerField(
        _('passing score (%)'),
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Gamification
    points_reward = models.IntegerField(_('points reward'), default=50, validators=[MinValueValidator(0)])

    # Module status
    is_active = models.BooleanField(_('active'), default=True)
    is_preview = models.BooleanField(_('preview available'), default=False)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('learning module')
        verbose_name_plural = _('learning modules')
        ordering = ['career_path', 'module_number']
        unique_together = ['career_path', 'module_number']

    def __str__(self):
        return f"{self.career_path.name} - Module {self.module_number}: {self.title}"

    def get_quiz(self):
        """Get the associated quiz for this module"""
        try:
            return self.quiz
        except Quiz.DoesNotExist:
            return None

    def get_completion_rate(self):
        """Calculate completion rate for this module"""
        total_started = self.user_progress.count()
        if total_started == 0:
            return 0
        completed = self.user_progress.filter(is_completed=True).count()
        return (completed / total_started) * 100


class Quiz(models.Model):
    """
    Model representing quizzes and assessments for learning modules
    with multiple question types and auto-grading.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.OneToOneField(
        LearningModule,
        on_delete=models.CASCADE,
        related_name='quiz',
        verbose_name=_('module')
    )
    title = models.CharField(_('quiz title'), max_length=200)
    description = models.TextField(_('quiz description'), blank=True)
    instructions = models.TextField(_('instructions'), blank=True)

    # Quiz configuration
    time_limit = models.IntegerField(
        _('time limit (minutes)'),
        blank=True,
        null=True,
        help_text=_('Leave blank for no time limit')
    )
    max_attempts = models.IntegerField(
        _('maximum attempts'),
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    passing_score = models.IntegerField(
        _('passing score (%)'),
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Question randomization
    randomize_questions = models.BooleanField(_('randomize questions'), default=False)
    questions_per_attempt = models.IntegerField(
        _('questions per attempt'),
        blank=True,
        null=True,
        help_text=_('Leave blank to show all questions')
    )

    # Availability
    is_active = models.BooleanField(_('active'), default=True)
    available_from = models.DateTimeField(_('available from'), blank=True, null=True)
    available_until = models.DateTimeField(_('available until'), blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('quiz')
        verbose_name_plural = _('quizzes')

    def __str__(self):
        return f"Quiz: {self.title}"

    def get_total_questions(self):
        """Get total number of questions in this quiz"""
        return self.questions.count()

    def get_average_score(self):
        """Calculate average score for this quiz"""
        attempts = self.attempts.filter(is_completed=True)
        if not attempts:
            return 0
        return sum(attempt.score for attempt in attempts) / len(attempts)


class Question(models.Model):
    """
    Model representing individual quiz questions with multiple types
    and auto-grading capabilities.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('quiz')
    )
    question_text = models.TextField(_('question text'))
    question_type = models.CharField(
        _('question type'),
        max_length=20,
        choices=[
            ('multiple_choice', 'Multiple Choice'),
            ('true_false', 'True/False'),
            ('short_answer', 'Short Answer'),
            ('code_completion', 'Code Completion'),
            ('multiple_select', 'Multiple Select'),
        ]
    )

    # Question content
    code_snippet = models.TextField(_('code snippet'), blank=True, help_text=_('Code for code-related questions'))
    explanation = models.TextField(_('explanation'), blank=True, help_text=_('Explanation shown after answering'))

    # Points and difficulty
    points = models.IntegerField(_('points'), default=1, validators=[MinValueValidator(1)])
    difficulty_level = models.CharField(
        _('difficulty level'),
        max_length=20,
        choices=[
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard'),
        ],
        default='medium'
    )

    # Question order and randomization
    order = models.IntegerField(_('order'), validators=[MinValueValidator(1)])
    is_active = models.BooleanField(_('active'), default=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('question')
        verbose_name_plural = _('questions')
        ordering = ['quiz', 'order']
        unique_together = ['quiz', 'order']

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."

    def get_choices(self):
        """Get all choices for this question"""
        return self.choices.all()

    def check_answer(self, user_answer):
        """Check if user answer is correct (for auto-gradable questions)"""
        if self.question_type in ['multiple_choice', 'true_false']:
            correct_choice = self.choices.filter(is_correct=True).first()
            return user_answer == correct_choice.id
        elif self.question_type == 'multiple_select':
            correct_choices = self.choices.filter(is_correct=True).values_list('id', flat=True)
            return set(user_answer) == set(correct_choices)
        # Short answer and code completion require manual grading
        return None


class QuestionChoice(models.Model):
    """
    Model representing answer choices for multiple choice questions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name=_('question')
    )
    choice_text = models.CharField(_('choice text'), max_length=500)
    is_correct = models.BooleanField(_('correct answer'), default=False)
    explanation = models.TextField(_('explanation'), blank=True)
    order = models.IntegerField(_('order'), validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = _('question choice')
        verbose_name_plural = _('question choices')
        ordering = ['question', 'order']
        unique_together = ['question', 'order']

    def __str__(self):
        return f"{self.choice_text} ({'Correct' if self.is_correct else 'Incorrect'})"


class UserProgress(models.Model):
    """
    Model tracking user progress through career paths and modules.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_progress',
        verbose_name=_('user')
    )
    career_path = models.ForeignKey(
        CareerPath,
        on_delete=models.CASCADE,
        related_name='user_progress',
        verbose_name=_('career path')
    )
    current_module = models.ForeignKey(
        LearningModule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_progress',
        verbose_name=_('current module')
    )

    # Progress tracking
    modules_completed = models.ManyToManyField(
        LearningModule,
        blank=True,
        related_name='completed_by_users',
        verbose_name=_('completed modules')
    )
    total_points_earned = models.IntegerField(_('total points earned'), default=0)
    is_completed = models.BooleanField(_('completed'), default=False)
    completion_date = models.DateTimeField(_('completion date'), blank=True, null=True)

    # Timestamps
    started_at = models.DateTimeField(_('started at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('user progress')
        verbose_name_plural = _('user progress')
        unique_together = ['user', 'career_path']

    def __str__(self):
        return f"{self.user.email} - {self.career_path.name}"

    def get_progress_percentage(self):
        """Calculate overall progress percentage"""
        total_modules = self.career_path.modules.filter(is_active=True).count()
        if total_modules == 0:
            return 0
        completed = self.modules_completed.count()
        return (completed / total_modules) * 100

    def mark_module_completed(self, module):
        """Mark a module as completed and update progress"""
        if module not in self.modules_completed.all():
            self.modules_completed.add(module)
            self.total_points_earned += module.points_reward
            self.user.add_points(module.points_reward)

            # Check if career path is completed
            total_modules = self.career_path.modules.filter(is_active=True).count()
            if self.modules_completed.count() >= total_modules:
                self.is_completed = True
                self.completion_date = models.timezone.now()
                self.user.add_points(self.career_path.points_reward)

            self.save()


class QuizAttempt(models.Model):
    """
    Model tracking individual quiz attempts by users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts',
        verbose_name=_('user')
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name=_('quiz')
    )

    # Attempt details
    started_at = models.DateTimeField(_('started at'), auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)
    time_taken = models.IntegerField(_('time taken (seconds)'), blank=True, null=True)

    # Scoring
    score = models.IntegerField(_('score (%)'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_passed = models.BooleanField(_('passed'), default=False)
    is_completed = models.BooleanField(_('completed'), default=False)

    # Attempt metadata
    attempt_number = models.IntegerField(_('attempt number'), validators=[MinValueValidator(1)])
    ip_address = models.GenericIPAddressField(_('IP address'), blank=True, null=True)

    class Meta:
        verbose_name = _('quiz attempt')
        verbose_name_plural = _('quiz attempts')
        unique_together = ['user', 'quiz', 'attempt_number']
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.email} - {self.quiz.title} (Attempt {self.attempt_number})"

    def calculate_score(self):
        """Calculate and update the quiz score"""
        if not self.is_completed:
            return

        total_questions = self.answers.count()
        if total_questions == 0:
            self.score = 0
        else:
            correct_answers = self.answers.filter(is_correct=True).count()
            self.score = int((correct_answers / total_questions) * 100)

        self.is_passed = self.score >= self.quiz.passing_score
        self.save()


class Answer(models.Model):
    """
    Model representing individual answers to quiz questions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('quiz attempt')
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='user_answers',
        verbose_name=_('question')
    )

    # Answer content
    answer_text = models.TextField(_('answer text'), blank=True)
    selected_choices = models.ManyToManyField(
        QuestionChoice,
        blank=True,
        related_name='selected_answers',
        verbose_name=_('selected choices')
    )

    # Answer validation
    is_correct = models.BooleanField(_('correct'), default=False)
    points_earned = models.IntegerField(_('points earned'), default=0)

    # Timestamps
    answered_at = models.DateTimeField(_('answered at'), auto_now_add=True)

    class Meta:
        verbose_name = _('answer')
        verbose_name_plural = _('answers')
        unique_together = ['attempt', 'question']

    def __str__(self):
        return f"Answer to: {self.question.question_text[:50]}..."

    def save(self, *args, **kwargs):
        """Override save to calculate correctness and points"""
        if self.question.question_type in ['multiple_choice', 'true_false']:
            correct_choice = self.question.choices.filter(is_correct=True).first()
            self.is_correct = correct_choice in self.selected_choices.all()
        elif self.question.question_type == 'multiple_select':
            correct_choices = self.question.choices.filter(is_correct=True)
            self.is_correct = set(self.selected_choices.all()) == set(correct_choices)
        else:
            # Manual grading required for short answer and code completion
            self.is_correct = None

        if self.is_correct is True:
            self.points_earned = self.question.points

        super().save(*args, **kwargs)
