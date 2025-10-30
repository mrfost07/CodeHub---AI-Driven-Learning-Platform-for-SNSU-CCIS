from rest_framework import serializers
from .models import (
    Project, ProjectMembership, ProjectTask, TaskLabel, ProjectTag,
    ProjectFile, CodeReview, ReviewAssignment, ReviewComment, ProjectActivity
)
from accounts.serializers import UserProfileSerializer


class ProjectTagSerializer(serializers.ModelSerializer):
    """Serializer for ProjectTag model"""

    class Meta:
        model = ProjectTag
        fields = ['id', 'name', 'description', 'color']
        read_only_fields = ['id']


class TaskLabelSerializer(serializers.ModelSerializer):
    """Serializer for TaskLabel model"""

    class Meta:
        model = TaskLabel
        fields = ['id', 'name', 'color', 'description', 'project']
        read_only_fields = ['id']


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model"""
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    member_count = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    tags = ProjectTagSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'slug', 'description', 'is_snsu_ccis_project',
            'course_related', 'course_code', 'owner', 'owner_name',
            'project_type', 'programming_language', 'status', 'visibility',
            'github_url', 'gitlab_url', 'repository_provider', 'tags',
            'allow_forking', 'require_approval', 'member_count',
            'progress_percentage', 'created_at', 'updated_at',
            'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.get_member_count()

    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()


class ProjectMembershipSerializer(serializers.ModelSerializer):
    """Serializer for ProjectMembership model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ProjectMembership
        fields = [
            'id', 'project', 'user', 'user_name', 'user_email',
            'role', 'joined_at', 'invited_by', 'is_active'
        ]
        read_only_fields = ['id', 'joined_at']


class ProjectTaskSerializer(serializers.ModelSerializer):
    """Serializer for ProjectTask model"""
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    labels = TaskLabelSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectTask
        fields = [
            'id', 'project', 'title', 'description', 'assigned_to',
            'assigned_to_name', 'status', 'priority', 'task_type', 'labels',
            'estimated_hours', 'actual_hours', 'order', 'column_order',
            'due_date', 'is_overdue', 'created_at', 'updated_at',
            'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'started_at', 'completed_at']


class ProjectFileSerializer(serializers.ModelSerializer):
    """Serializer for ProjectFile model"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectFile
        fields = [
            'id', 'project', 'file', 'filename', 'file_path', 'file_size',
            'mime_type', 'file_extension', 'version', 'parent_version',
            'description', 'category', 'uploaded_by', 'uploaded_by_name',
            'is_active', 'file_url', 'uploaded_at', 'modified_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at', 'modified_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            url = obj.file.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class ReviewCommentSerializer(serializers.ModelSerializer):
    """Serializer for ReviewComment model"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = ReviewComment
        fields = [
            'id', 'review', 'author', 'author_name', 'comment_text',
            'file_path', 'line_number', 'comment_type', 'created_at',
            'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class ReviewAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for ReviewAssignment model"""
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)

    class Meta:
        model = ReviewAssignment
        fields = [
            'id', 'review', 'reviewer', 'reviewer_name', 'status',
            'comments', 'assigned_at', 'completed_at'
        ]
        read_only_fields = ['id', 'assigned_at']


class CodeReviewSerializer(serializers.ModelSerializer):
    """Serializer for CodeReview model"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    comments = ReviewCommentSerializer(many=True, read_only=True)
    assignments = ReviewAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = CodeReview
        fields = [
            'id', 'project', 'title', 'description', 'files_changed',
            'diff_content', 'status', 'author', 'author_name',
            'branch_name', 'commit_hash', 'comments', 'assignments',
            'created_at', 'updated_at', 'reviewed_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class ProjectActivitySerializer(serializers.ModelSerializer):
    """Serializer for ProjectActivity model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = ProjectActivity
        fields = [
            'id', 'project', 'user', 'user_name', 'activity_type',
            'description', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class ProjectDetailSerializer(ProjectSerializer):
    """Detailed serializer for Project model with nested data"""
    team_members = ProjectMembershipSerializer(source='memberships', many=True, read_only=True)
    recent_activities = serializers.SerializerMethodField()
    active_tasks_count = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + [
            'team_members', 'recent_activities', 'active_tasks_count'
        ]

    def get_recent_activities(self, obj):
        activities = obj.activities.all()[:10]
        return ProjectActivitySerializer(activities, many=True).data

    def get_active_tasks_count(self, obj):
        return obj.get_active_tasks().count()

