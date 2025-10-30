import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """
    Custom User model extending AbstractUser with UUID primary key and additional fields
    for the CodeHub learning platform.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        _('user role'),
        max_length=20,
        choices=[
            ('admin', 'Administrator'),
            ('instructor', 'Instructor'),
            ('student', 'Student'),
            ('guest', 'Guest'),
            ('moderator', 'Moderator'),
        ],
        default='student',
        help_text=_('User role determines permissions and access level')
    )
    program = models.CharField(
        _('academic program'),
        max_length=50,
        choices=[
            ('bsit', 'Bachelor of Science in Information Technology'),
            ('bscs', 'Bachelor of Science in Computer Science'),
            ('bsis', 'Bachelor of Science in Information Systems'),
            ('other', 'Other'),
        ],
        blank=True,
        null=True,
        help_text=_('Academic program for students')
    )
    year_level = models.IntegerField(
        _('year level'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True,
        help_text=_('Current year level (1-5)')
    )
    student_id = models.CharField(
        _('student ID'),
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Official student identification number')
    )

    # Profile fields
    bio = models.TextField(_('biography'), blank=True, max_length=500)
    avatar = models.ImageField(_('avatar'), upload_to='avatars/', blank=True, null=True)
    github_username = models.CharField(_('GitHub username'), max_length=39, blank=True)
    linkedin_url = models.URLField(_('LinkedIn URL'), blank=True)
    portfolio_url = models.URLField(_('portfolio URL'), blank=True)

    # Skills and interests
    skills = models.ManyToManyField(
        'Skill',
        verbose_name=_('skills'),
        blank=True,
        related_name='users',
        help_text=_('Technical skills and competencies')
    )
    career_interests = models.ManyToManyField(
        'CareerInterest',
        verbose_name=_('career interests'),
        blank=True,
        related_name='users',
        help_text=_('Career goals and interests')
    )

    # Gamification
    points = models.IntegerField(_('points'), default=0, validators=[MinValueValidator(0)])
    level = models.IntegerField(_('level'), default=1, validators=[MinValueValidator(1)])
    badges = models.ManyToManyField(
        'Badge',
        verbose_name=_('badges'),
        blank=True,
        related_name='users',
        help_text=_('Earned badges and achievements')
    )

    # Social features
    following = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='followers',
        blank=True,
        help_text=_('Users this user is following')
    )
    is_verified = models.BooleanField(_('verified'), default=False)
    is_active = models.BooleanField(_('active'), default=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    # Use email as username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_role_display(self):
        return dict(self._meta.get_field('role').choices)[self.role]

    def get_program_display(self):
        if self.program:
            return dict(self._meta.get_field('program').choices)[self.program]
        return None

    def follow(self, user):
        """Follow another user"""
        if user != self and not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        """Unfollow a user"""
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        """Check if this user is following another user"""
        return self.following.filter(pk=user.pk).exists()

    def get_followers_count(self):
        """Get count of followers"""
        return self.followers.count()

    def get_following_count(self):
        """Get count of users this user is following"""
        return self.following.count()

    def add_points(self, points_to_add):
        """Add points and update level"""
        self.points += points_to_add
        # Level calculation: every 1000 points = 1 level
        self.level = (self.points // 1000) + 1
        self.save(update_fields=['points', 'level'])

    def has_permission(self, permission):
        """Check if user has specific permission based on role"""
        role_permissions = {
            'admin': [
                'manage_users', 'manage_content', 'manage_system',
                'view_analytics', 'moderate_content', 'manage_courses'
            ],
            'instructor': [
                'create_content', 'manage_own_courses', 'grade_assignments',
                'view_student_progress', 'moderate_own_content'
            ],
            'moderator': [
                'moderate_content', 'manage_reports', 'view_user_activity'
            ],
            'student': [
                'access_courses', 'submit_assignments', 'join_projects',
                'participate_community', 'earn_points'
            ],
            'guest': [
                'view_public_content', 'basic_browse'
            ]
        }
        return permission in role_permissions.get(self.role, [])


class Skill(models.Model):
    """Model for technical skills that users can have"""
    name = models.CharField(_('skill name'), max_length=50, unique=True)
    category = models.CharField(
        _('category'),
        max_length=30,
        choices=[
            ('programming', 'Programming Languages'),
            ('frameworks', 'Frameworks & Libraries'),
            ('databases', 'Databases'),
            ('tools', 'Tools & Software'),
            ('cloud', 'Cloud & DevOps'),
            ('design', 'Design & UI/UX'),
            ('other', 'Other'),
        ]
    )
    description = models.TextField(_('description'), blank=True)
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('skill')
        verbose_name_plural = _('skills')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category})"


class CareerInterest(models.Model):
    """Model for career interests and goals"""
    name = models.CharField(_('interest name'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True)
    industry = models.CharField(
        _('industry'),
        max_length=50,
        choices=[
            ('software_development', 'Software Development'),
            ('data_science', 'Data Science & Analytics'),
            ('cybersecurity', 'Cybersecurity'),
            ('networking', 'Networking & Infrastructure'),
            ('ui_ux_design', 'UI/UX Design'),
            ('project_management', 'Project Management'),
            ('consulting', 'IT Consulting'),
            ('academia', 'Academia & Research'),
            ('entrepreneurship', 'Entrepreneurship'),
            ('other', 'Other'),
        ]
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('career interest')
        verbose_name_plural = _('career interests')
        ordering = ['industry', 'name']

    def __str__(self):
        return f"{self.name} ({self.industry})"


class Badge(models.Model):
    """Model for badges and achievements"""
    name = models.CharField(_('badge name'), max_length=50, unique=True)
    description = models.TextField(_('description'))
    icon = models.CharField(_('icon class'), max_length=50, help_text=_('CSS icon class or emoji'))
    badge_type = models.CharField(
        _('badge type'),
        max_length=20,
        choices=[
            ('learning', 'Learning Achievement'),
            ('project', 'Project Contribution'),
            ('community', 'Community Engagement'),
            ('skill', 'Skill Development'),
            ('special', 'Special Achievement'),
        ]
    )
    points_required = models.IntegerField(_('points required'), default=0)
    criteria = models.TextField(_('criteria'), help_text=_('Description of how to earn this badge'))
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('badge')
        verbose_name_plural = _('badges')
        ordering = ['badge_type', 'points_required']

    def __str__(self):
        return self.name
