import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import json


class Project(models.Model):
    """
    Model representing collaborative projects with team management,
    real-time editing, and version control integration.
    Specifically designed for SNSU CCIS students.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('project name'), max_length=200)
    slug = models.SlugField(_('slug'), max_length=200, unique=True)
    description = models.TextField(_('description'))
    
    # SNSU CCIS specific fields
    is_snsu_ccis_project = models.BooleanField(_('SNSU CCIS project'), default=True)
    course_related = models.BooleanField(_('course related'), default=False)
    course_code = models.CharField(_('course code'), max_length=20, blank=True)

    # Project ownership and team
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_projects',
        verbose_name=_('project owner')
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectMembership',
        through_fields=('project', 'user'),
        related_name='team_projects',
        verbose_name=_('team members'),
        blank=True
    )

    # Project configuration
    project_type = models.CharField(
        _('project type'),
        max_length=30,
        choices=[
            ('web_application', 'Web Application'),
            ('mobile_app', 'Mobile Application'),
            ('desktop_app', 'Desktop Application'),
            ('api', 'API/Service'),
            ('data_science', 'Data Science Project'),
            ('machine_learning', 'Machine Learning Project'),
            ('game', 'Game Development'),
            ('other', 'Other'),
        ]
    )
    programming_language = models.CharField(
        _('primary language'),
        max_length=30,
        choices=[
            ('python', 'Python'),
            ('javascript', 'JavaScript'),
            ('typescript', 'TypeScript'),
            ('java', 'Java'),
            ('csharp', 'C#'),
            ('cpp', 'C++'),
            ('php', 'PHP'),
            ('ruby', 'Ruby'),
            ('go', 'Go'),
            ('rust', 'Rust'),
            ('swift', 'Swift'),
            ('kotlin', 'Kotlin'),
            ('other', 'Other'),
        ]
    )

    # Project status and visibility
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('planning', 'Planning'),
            ('in_progress', 'In Progress'),
            ('review', 'Under Review'),
            ('completed', 'Completed'),
            ('on_hold', 'On Hold'),
            ('cancelled', 'Cancelled'),
        ],
        default='planning'
    )
    visibility = models.CharField(
        _('visibility'),
        max_length=20,
        choices=[
            ('private', 'Private'),
            ('team', 'Team Only'),
            ('public', 'Public'),
        ],
        default='private'
    )

    # Repository integration
    github_url = models.URLField(_('GitHub URL'), blank=True)
    gitlab_url = models.URLField(_('GitLab URL'), blank=True)
    repository_provider = models.CharField(
        _('repository provider'),
        max_length=20,
        choices=[
            ('github', 'GitHub'),
            ('gitlab', 'GitLab'),
            ('bitbucket', 'Bitbucket'),
            ('none', 'No Integration'),
        ],
        default='none'
    )

    # Project metadata
    technologies = models.ManyToManyField(
        'accounts.Skill',
        blank=True,
        related_name='used_in_projects',
        verbose_name=_('technologies used')
    )
    tags = models.ManyToManyField(
        'ProjectTag',
        blank=True,
        related_name='projects',
        verbose_name=_('tags')
    )

    # Project settings
    allow_forking = models.BooleanField(_('allow forking'), default=False)
    require_approval = models.BooleanField(_('require approval for changes'), default=False)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    started_at = models.DateTimeField(_('started at'), blank=True, null=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)

    class Meta:
        verbose_name = _('project')
        verbose_name_plural = _('projects')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_member_count(self):
        """Get total number of team members"""
        return self.team_members.count()

    def get_active_tasks(self):
        """Get all active (non-completed) tasks"""
        return self.tasks.filter(status__in=['todo', 'in_progress', 'review'])

    def get_completed_tasks(self):
        """Get all completed tasks"""
        return self.tasks.filter(status='completed')

    def get_progress_percentage(self):
        """Calculate project progress based on task completion"""
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        completed_tasks = self.tasks.filter(status='completed').count()
        return (completed_tasks / total_tasks) * 100

    def add_member(self, user, role='member'):
        """Add a user to the project team"""
        membership, created = ProjectMembership.objects.get_or_create(
            project=self,
            user=user,
            defaults={'role': role}
        )
        return membership

    def remove_member(self, user):
        """Remove a user from the project team"""
        ProjectMembership.objects.filter(project=self, user=user).delete()

    def is_member(self, user):
        """Check if user is a team member"""
        return self.team_members.filter(id=user.id).exists()

    def can_user_edit(self, user):
        """Check if user can edit project files"""
        if user == self.owner:
            return True
        if not self.is_member(user):
            return False
        membership = ProjectMembership.objects.get(project=self, user=user)
        return membership.role in ['editor', 'admin']

    def can_user_administer(self, user):
        """Check if user can administer project"""
        if user == self.owner:
            return True
        if not self.is_member(user):
            return False
        membership = ProjectMembership.objects.get(project=self, user=user)
        return membership.role == 'admin'


class ProjectMembership(models.Model):
    """
    Model representing user membership and roles in projects.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships'
    )
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=[
            ('viewer', 'Viewer'),
            ('member', 'Member'),
            ('editor', 'Editor'),
            ('admin', 'Administrator'),
        ],
        default='member'
    )

    # Membership details
    joined_at = models.DateTimeField(_('joined at'), auto_now_add=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='project_invitations_sent'
    )
    is_active = models.BooleanField(_('active'), default=True)

    class Meta:
        verbose_name = _('project membership')
        verbose_name_plural = _('project memberships')
        unique_together = ['project', 'user']

    def __str__(self):
        return f"{self.user.email} - {self.project.name} ({self.role})"


class ProjectTask(models.Model):
    """
    Model representing tasks within a project for team collaboration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_('project')
    )
    title = models.CharField(_('task title'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    
    # Task assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name=_('assigned to')
    )
    
    # Task status and priority
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('todo', 'To Do'),
            ('in_progress', 'In Progress'),
            ('review', 'Under Review'),
            ('completed', 'Completed'),
        ],
        default='todo'
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='medium'
    )

    # Task metadata
    task_type = models.CharField(
        _('task type'),
        max_length=30,
        choices=[
            ('feature', 'Feature'),
            ('bug', 'Bug Fix'),
            ('enhancement', 'Enhancement'),
            ('documentation', 'Documentation'),
            ('testing', 'Testing'),
            ('deployment', 'Deployment'),
            ('other', 'Other'),
        ],
        default='feature'
    )
    labels = models.ManyToManyField(
        'TaskLabel',
        blank=True,
        related_name='tasks',
        verbose_name=_('labels')
    )

    # Task estimation and tracking
    estimated_hours = models.DecimalField(
        _('estimated hours'),
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        validators=[MinValueValidator(0.1)]
    )
    actual_hours = models.DecimalField(
        _('actual hours'),
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)]
    )

    # Task ordering and positioning
    order = models.IntegerField(_('order'), default=0)
    column_order = models.IntegerField(_('column order'), default=0)

    # Due dates and deadlines
    due_date = models.DateField(_('due date'), blank=True, null=True)
    is_overdue = models.BooleanField(_('overdue'), default=False)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    started_at = models.DateTimeField(_('started at'), blank=True, null=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)

    class Meta:
        verbose_name = _('project task')
        verbose_name_plural = _('project tasks')
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.project.name} - {self.title}"

    def save(self, *args, **kwargs):
        """Override save to update status timestamps"""
        if self.status == 'in_progress' and not self.started_at:
            self.started_at = models.timezone.now()
        elif self.status == 'completed' and not self.completed_at:
            self.completed_at = models.timezone.now()

        super().save(*args, **kwargs)

    def get_time_spent(self):
        """Calculate time spent on task"""
        if self.actual_hours:
            return self.actual_hours
        return 0

    def is_assigned_to_user(self, user):
        """Check if task is assigned to specific user"""
        return self.assigned_to == user if self.assigned_to else False


class TaskLabel(models.Model):
    """
    Model representing labels/tags for project tasks.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('label name'), max_length=50, unique=True)
    color = models.CharField(_('color code'), max_length=7, default='#007bff')
    description = models.TextField(_('description'), blank=True)

    # Label scope
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='available_labels',
        null=True,
        blank=True,
        help_text=_('Leave blank for global labels')
    )

    class Meta:
        verbose_name = _('task label')
        verbose_name_plural = _('task labels')

    def __str__(self):
        return self.name


class ProjectTag(models.Model):
    """
    Model representing tags for categorizing projects.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tag name'), max_length=50, unique=True)
    description = models.TextField(_('description'), blank=True)
    color = models.CharField(_('color code'), max_length=7, default='#6c757d')

    class Meta:
        verbose_name = _('project tag')
        verbose_name_plural = _('project tags')

    def __str__(self):
        return self.name


class ProjectFile(models.Model):
    """
    Model representing files uploaded to projects with version management.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name=_('project')
    )
    file = models.FileField(_('file'), upload_to='project_files/')
    filename = models.CharField(_('filename'), max_length=255)
    file_path = models.CharField(_('file path'), max_length=500)

    # File metadata
    file_size = models.BigIntegerField(_('file size'), validators=[MinValueValidator(0)])
    mime_type = models.CharField(_('MIME type'), max_length=100)
    file_extension = models.CharField(_('file extension'), max_length=10)

    # File versioning
    version = models.IntegerField(_('version'), default=1)
    parent_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='next_versions'
    )

    # File description and categorization
    description = models.TextField(_('description'), blank=True)
    category = models.CharField(
        _('category'),
        max_length=30,
        choices=[
            ('source_code', 'Source Code'),
            ('documentation', 'Documentation'),
            ('design', 'Design Assets'),
            ('configuration', 'Configuration'),
            ('data', 'Data Files'),
            ('other', 'Other'),
        ],
        default='other'
    )

    # Upload details
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_files'
    )
    is_active = models.BooleanField(_('active'), default=True)

    # Timestamps
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)

    class Meta:
        verbose_name = _('project file')
        verbose_name_plural = _('project files')
        ordering = ['file_path', '-version']

    def __str__(self):
        return f"{self.filename} (v{self.version})"

    def get_file_url(self):
        """Get the URL for file download"""
        return self.file.url

    def get_versions(self):
        """Get all versions of this file"""
        if self.parent_version:
            return [self.parent_version] + list(self.parent_version.get_versions())
        return [self]


class CodeReview(models.Model):
    """
    Model representing code review requests and feedback.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='code_reviews',
        verbose_name=_('project')
    )
    title = models.CharField(_('review title'), max_length=200)
    description = models.TextField(_('review description'))

    # Review files and changes
    files_changed = models.JSONField(_('files changed'), default=list)
    diff_content = models.TextField(_('diff content'), blank=True)

    # Review status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('in_review', 'In Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('changes_requested', 'Changes Requested'),
        ],
        default='pending'
    )

    # Review participants
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authored_reviews'
    )
    reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ReviewAssignment',
        related_name='assigned_reviews',
        blank=True
    )

    # Review metadata
    branch_name = models.CharField(_('branch name'), max_length=100, blank=True)
    commit_hash = models.CharField(_('commit hash'), max_length=40, blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    reviewed_at = models.DateTimeField(_('reviewed at'), blank=True, null=True)

    class Meta:
        verbose_name = _('code review')
        verbose_name_plural = _('code reviews')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.title}"

    def get_review_comments(self):
        """Get all comments for this review"""
        return self.comments.filter(is_active=True)

    def get_approval_status(self):
        """Get overall approval status from reviewers"""
        assignments = self.assignments.filter(status__in=['approved', 'rejected'])
        if not assignments:
            return 'pending'

        approved = assignments.filter(status='approved').count()
        total = assignments.count()

        if approved == total:
            return 'approved'
        elif assignments.filter(status='rejected').exists():
            return 'rejected'
        else:
            return 'partial'


class ReviewAssignment(models.Model):
    """
    Model representing reviewer assignments for code reviews.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        CodeReview,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_assignments'
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('changes_requested', 'Changes Requested'),
        ],
        default='pending'
    )

    # Review feedback
    comments = models.TextField(_('reviewer comments'), blank=True)
    assigned_at = models.DateTimeField(_('assigned at'), auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)

    class Meta:
        verbose_name = _('review assignment')
        verbose_name_plural = _('review assignments')
        unique_together = ['review', 'reviewer']

    def __str__(self):
        return f"{self.reviewer.email} - {self.review.title}"


class ReviewComment(models.Model):
    """
    Model representing comments and feedback on code reviews.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        CodeReview,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_comments'
    )

    # Comment content
    comment_text = models.TextField(_('comment'))
    file_path = models.CharField(_('file path'), max_length=500, blank=True)
    line_number = models.IntegerField(_('line number'), blank=True, null=True)

    # Comment metadata
    comment_type = models.CharField(
        _('comment type'),
        max_length=20,
        choices=[
            ('general', 'General Comment'),
            ('suggestion', 'Suggestion'),
            ('issue', 'Issue'),
            ('praise', 'Praise'),
        ],
        default='general'
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    is_active = models.BooleanField(_('active'), default=True)

    class Meta:
        verbose_name = _('review comment')
        verbose_name_plural = _('review comments')
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.email} on {self.review.title}"


class ProjectActivity(models.Model):
    """
    Model tracking activities and changes within projects.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_activities'
    )

    # Activity details
    activity_type = models.CharField(
        _('activity type'),
        max_length=30,
        choices=[
            ('project_created', 'Project Created'),
            ('member_added', 'Member Added'),
            ('member_removed', 'Member Removed'),
            ('task_created', 'Task Created'),
            ('task_updated', 'Task Updated'),
            ('task_completed', 'Task Completed'),
            ('file_uploaded', 'File Uploaded'),
            ('file_updated', 'File Updated'),
            ('review_created', 'Review Created'),
            ('review_approved', 'Review Approved'),
            ('comment_added', 'Comment Added'),
        ]
    )

    # Activity metadata
    description = models.TextField(_('description'))
    metadata = models.JSONField(_('metadata'), default=dict)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('project activity')
        verbose_name_plural = _('project activities')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.activity_type} - {self.project.name}"
