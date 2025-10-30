import uuid
import re
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.urls import reverse


class Post(models.Model):
    """
    Model representing community posts with rich content support,
    threaded comments, and engagement features.
    Specifically designed for SNSU CCIS community interaction.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name=_('author')
    )

    # Post content
    title = models.CharField(_('post title'), max_length=200)
    content = models.TextField(_('post content'))
    content_type = models.CharField(
        _('content type'),
        max_length=20,
        choices=[
            ('text', 'Text Only'),
            ('image', 'Image Post'),
            ('code', 'Code Snippet'),
            ('project', 'Project Showcase'),
            ('question', 'Question'),
            ('announcement', 'Announcement'),
            ('mixed', 'Mixed Content'),
        ],
        default='text'
    )
    
    # SNSU CCIS specific fields
    is_faculty_announcement = models.BooleanField(_('faculty announcement'), default=False)
    is_official = models.BooleanField(_('official SNSU CCIS post'), default=False)
    program_relevance = models.CharField(
        _('program relevance'),
        max_length=20,
        choices=[
            ('all', 'All Programs'),
            ('bsit', 'BS Information Technology'),
            ('bscs', 'BS Computer Science'),
            ('bsis', 'BS Information Systems'),
        ],
        default='all'
    )

    # Media attachments
    image = models.ImageField(_('featured image'), upload_to='post_images/', blank=True, null=True)
    code_snippet = models.TextField(_('code snippet'), blank=True)
    code_language = models.CharField(_('code language'), max_length=30, blank=True)

    # Project association (optional)
    related_project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_posts',
        verbose_name=_('related project')
    )

    # Learning association (optional)
    related_module = models.ForeignKey(
        'learning.LearningModule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_posts',
        verbose_name=_('related module')
    )

    # Post metadata
    tags = models.ManyToManyField(
        'PostTag',
        blank=True,
        related_name='posts',
        verbose_name=_('tags')
    )
    hashtags = models.ManyToManyField(
        'Hashtag',
        blank=True,
        related_name='posts',
        verbose_name=_('hashtags')
    )

    # Engagement metrics
    likes_count = models.IntegerField(_('likes count'), default=0)
    comments_count = models.IntegerField(_('comments count'), default=0)
    shares_count = models.IntegerField(_('shares count'), default=0)
    views_count = models.IntegerField(_('views count'), default=0)

    # Post status and moderation
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('hidden', 'Hidden'),
            ('moderated', 'Under Moderation'),
            ('removed', 'Removed'),
        ],
        default='draft'
    )
    is_pinned = models.BooleanField(_('pinned'), default=False)
    is_featured = models.BooleanField(_('featured'), default=False)

    # Visibility and access
    visibility = models.CharField(
        _('visibility'),
        max_length=20,
        choices=[
            ('public', 'Public'),
            ('followers', 'Followers Only'),
            ('private', 'Private'),
        ],
        default='public'
    )

    # Moderation
    moderation_reason = models.TextField(_('moderation reason'), blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='moderated_posts'
    )
    moderated_at = models.DateTimeField(_('moderated at'), blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    published_at = models.DateTimeField(_('published at'), blank=True, null=True)

    class Meta:
        verbose_name = _('post')
        verbose_name_plural = _('posts')
        ordering = ['-is_pinned', '-published_at', '-created_at']

    def __str__(self):
        return f"{self.author.email} - {self.title}"

    def save(self, *args, **kwargs):
        """Override save to extract hashtags and update published_at"""
        if self.status == 'published' and not self.published_at:
            self.published_at = models.timezone.now()

        # Extract hashtags from content
        super().save(*args, **kwargs)
        self.extract_hashtags()

    def extract_hashtags(self):
        """Extract hashtags from post content and title"""
        hashtag_pattern = r'#(\w+)'
        hashtags = set()

        # Extract from title and content
        text_to_search = f"{self.title} {self.content}"
        found_hashtags = re.findall(hashtag_pattern, text_to_search)

        for tag in found_hashtags:
            hashtag, created = Hashtag.objects.get_or_create(
                name=tag.lower(),
                defaults={'description': f'Hashtag for #{tag}'}
            )
            hashtags.add(hashtag)

        # Update post hashtags
        self.hashtags.set(hashtags)

    def get_absolute_url(self):
        """Get the absolute URL for this post"""
        return reverse('post_detail', args=[str(self.id)])

    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])

    def like(self, user):
        """Like this post"""
        like, created = PostLike.objects.get_or_create(
            post=self,
            user=user
        )
        if created:
            self.likes_count += 1
            self.save(update_fields=['likes_count'])
        return created

    def unlike(self, user):
        """Unlike this post"""
        try:
            like = PostLike.objects.get(post=self, user=user)
            like.delete()
            self.likes_count -= 1
            self.save(update_fields=['likes_count'])
            return True
        except PostLike.DoesNotExist:
            return False

    def is_liked_by(self, user):
        """Check if post is liked by user"""
        return self.likes.filter(user=user).exists()

    def get_top_level_comments(self):
        """Get top-level comments (not replies)"""
        return self.comments.filter(parent_comment=None, is_active=True)

    def get_all_comments(self):
        """Get all comments including replies"""
        return self.comments.filter(is_active=True)

    def add_comment(self, user, content, parent_comment=None):
        """Add a comment to this post"""
        comment = Comment.objects.create(
            post=self,
            author=user,
            content=content,
            parent_comment=parent_comment
        )
        if parent_comment:
            parent_comment.replies_count += 1
            parent_comment.save()
        else:
            self.comments_count += 1
            self.save()
        return comment


class Comment(models.Model):
    """
    Model representing threaded comments on posts with moderation support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('post')
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('author')
    )

    # Comment content
    content = models.TextField(_('comment content'))
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('parent comment')
    )

    # Comment metadata
    likes_count = models.IntegerField(_('likes count'), default=0)
    replies_count = models.IntegerField(_('replies count'), default=0)
    mentions = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='CommentMention',
        related_name='mentioned_in_comments',
        blank=True
    )

    # Comment status
    is_active = models.BooleanField(_('active'), default=True)
    is_moderated = models.BooleanField(_('moderated'), default=False)
    moderation_reason = models.TextField(_('moderation reason'), blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    moderated_at = models.DateTimeField(_('moderated at'), blank=True, null=True)

    class Meta:
        verbose_name = _('comment')
        verbose_name_plural = _('comments')
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.email} on {self.post.title}"

    def like(self, user):
        """Like this comment"""
        like, created = CommentLike.objects.get_or_create(
            comment=self,
            user=user
        )
        if created:
            self.likes_count += 1
            self.save(update_fields=['likes_count'])
        return created

    def unlike(self, user):
        """Unlike this comment"""
        try:
            like = CommentLike.objects.get(comment=self, user=user)
            like.delete()
            self.likes_count -= 1
            self.save(update_fields=['likes_count'])
            return True
        except CommentLike.DoesNotExist:
            return False

    def is_liked_by(self, user):
        """Check if comment is liked by user"""
        return self.likes.filter(user=user).exists()

    def get_replies(self):
        """Get direct replies to this comment"""
        return self.replies.filter(is_active=True)

    def get_all_replies(self):
        """Get all nested replies"""
        replies = self.replies.filter(is_active=True)
        all_replies = list(replies)
        for reply in replies:
            all_replies.extend(reply.get_all_replies())
        return all_replies

    def extract_mentions(self):
        """Extract user mentions from comment content"""
        mention_pattern = r'@(\w+)'
        mentions = set()

        found_mentions = re.findall(mention_pattern, self.content)

        for username in found_mentions:
            try:
                user = settings.AUTH_USER_MODEL.objects.get(username=username)
                mentions.add(user)
            except settings.AUTH_USER_MODEL.DoesNotExist:
                pass  # User doesn't exist, skip

        # Update comment mentions
        self.mentions.set(mentions)


class PostLike(models.Model):
    """
    Model representing likes on posts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_likes'
    )
    created_at = models.DateTimeField(_('liked at'), auto_now_add=True)

    class Meta:
        verbose_name = _('post like')
        verbose_name_plural = _('post likes')
        unique_together = ['post', 'user']

    def __str__(self):
        return f"{self.user.email} likes {self.post.title}"


class CommentLike(models.Model):
    """
    Model representing likes on comments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_likes'
    )
    created_at = models.DateTimeField(_('liked at'), auto_now_add=True)

    class Meta:
        verbose_name = _('comment like')
        verbose_name_plural = _('comment likes')
        unique_together = ['comment', 'user']

    def __str__(self):
        return f"{self.user.email} likes comment on {self.comment.post.title}"


class CommentMention(models.Model):
    """
    Model representing user mentions in comments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='mention_relations'
    )
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_mentions'
    )
    created_at = models.DateTimeField(_('mentioned at'), auto_now_add=True)

    class Meta:
        verbose_name = _('comment mention')
        verbose_name_plural = _('comment mentions')
        unique_together = ['comment', 'mentioned_user']

    def __str__(self):
        return f"{self.mentioned_user.email} mentioned in comment"


class PostTag(models.Model):
    """
    Model representing tags for categorizing posts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tag name'), max_length=50, unique=True)
    description = models.TextField(_('description'), blank=True)
    color = models.CharField(_('color code'), max_length=7, default='#6c757d')
    is_active = models.BooleanField(_('active'), default=True)

    class Meta:
        verbose_name = _('post tag')
        verbose_name_plural = _('post tags')

    def __str__(self):
        return self.name


class Hashtag(models.Model):
    """
    Model representing hashtags extracted from post content.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('hashtag'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True)
    usage_count = models.IntegerField(_('usage count'), default=0)
    last_used = models.DateTimeField(_('last used'), auto_now=True)

    class Meta:
        verbose_name = _('hashtag')
        verbose_name_plural = _('hashtags')
        ordering = ['-usage_count', '-last_used']

    def __str__(self):
        return f"#{self.name}"

    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.last_used = models.timezone.now()
        self.save()


class Notification(models.Model):
    """
    Model representing real-time notifications for users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('recipient')
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        verbose_name=_('actor')
    )

    # Notification content
    notification_type = models.CharField(
        _('notification type'),
        max_length=30,
        choices=[
            ('post_like', 'Post Liked'),
            ('comment', 'New Comment'),
            ('comment_reply', 'Comment Reply'),
            ('comment_mention', 'Mentioned in Comment'),
            ('post_mention', 'Mentioned in Post'),
            ('project_invitation', 'Project Invitation'),
            ('project_update', 'Project Update'),
            ('achievement', 'Achievement Unlocked'),
            ('follow', 'New Follower'),
            ('system', 'System Notification'),
        ]
    )

    # Related objects
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    # Notification content
    title = models.CharField(_('notification title'), max_length=200)
    message = models.TextField(_('notification message'))

    # Notification metadata
    is_read = models.BooleanField(_('read'), default=False)
    is_sent = models.BooleanField(_('sent'), default=False)  # For email notifications
    action_url = models.URLField(_('action URL'), blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    read_at = models.DateTimeField(_('read at'), blank=True, null=True)

    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.email} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = models.timezone.now()
            self.save()

    def get_action_url(self):
        """Get URL for notification action"""
        if self.action_url:
            return self.action_url
        elif self.post:
            return self.post.get_absolute_url()
        elif self.project:
            return reverse('project_detail', args=[str(self.project.id)])
        return '/'

    def get_email_content(self):
        """Get content formatted for email"""
        return {
            'subject': self.title,
            'message': self.message,
            'action_url': self.get_action_url(),
            'created_at': self.created_at
        }


class UserFollow(models.Model):
    """
    Model representing user follow relationships.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following_relations'
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower_relations'
    )
    created_at = models.DateTimeField(_('followed at'), auto_now_add=True)

    class Meta:
        verbose_name = _('user follow')
        verbose_name_plural = _('user follows')
        unique_together = ['follower', 'following']

    def __str__(self):
        return f"{self.follower.email} follows {self.following.email}"


class Report(models.Model):
    """
    Model representing user reports for content moderation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    # Reported content
    reported_post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    reported_comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='user_reports'
    )

    # Report details
    report_type = models.CharField(
        _('report type'),
        max_length=30,
        choices=[
            ('spam', 'Spam'),
            ('harassment', 'Harassment'),
            ('inappropriate', 'Inappropriate Content'),
            ('copyright', 'Copyright Infringement'),
            ('misinformation', 'Misinformation'),
            ('other', 'Other'),
        ]
    )
    description = models.TextField(_('report description'))
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('investigating', 'Under Investigation'),
            ('resolved', 'Resolved'),
            ('dismissed', 'Dismissed'),
        ],
        default='pending'
    )

    # Moderation
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='moderated_reports'
    )
    moderation_notes = models.TextField(_('moderation notes'), blank=True)
    action_taken = models.TextField(_('action taken'), blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    resolved_at = models.DateTimeField(_('resolved at'), blank=True, null=True)

    class Meta:
        verbose_name = _('report')
        verbose_name_plural = _('reports')
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter.email} - {self.report_type}"
