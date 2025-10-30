from rest_framework import serializers
from .models import (
    Post, Comment, PostLike, CommentLike, PostTag, Hashtag,
    Notification, Report
)
from accounts.serializers import UserProfileSerializer


class PostTagSerializer(serializers.ModelSerializer):
    """Serializer for PostTag model"""

    class Meta:
        model = PostTag
        fields = ['id', 'name', 'description', 'color', 'is_active']
        read_only_fields = ['id']


class HashtagSerializer(serializers.ModelSerializer):
    """Serializer for Hashtag model"""

    class Meta:
        model = Hashtag
        fields = ['id', 'name', 'description', 'usage_count', 'last_used']
        read_only_fields = ['id', 'usage_count', 'last_used']


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)
    is_liked = serializers.SerializerMethodField()
    replies_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'author_name', 'author_avatar',
            'content', 'parent_comment', 'likes_count', 'replies_count',
            'is_active', 'is_moderated', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'likes_count', 'created_at', 'updated_at']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_liked_by(request.user)
        return False


class PostSerializer(serializers.ModelSerializer):
    """Serializer for Post model"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)
    tags = PostTagSerializer(many=True, read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_name', 'author_avatar', 'author_role',
            'title', 'content', 'content_type', 'is_faculty_announcement',
            'is_official', 'program_relevance', 'image', 'code_snippet',
            'code_language', 'related_project', 'related_module', 'tags',
            'hashtags', 'likes_count', 'comments_count', 'shares_count',
            'views_count', 'status', 'is_pinned', 'is_featured',
            'visibility', 'is_liked', 'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'id', 'author', 'likes_count', 'comments_count',
            'shares_count', 'views_count', 'created_at', 'updated_at', 'published_at'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_liked_by(request.user)
        return False


class PostDetailSerializer(PostSerializer):
    """Detailed serializer for Post model with comments"""
    top_comments = serializers.SerializerMethodField()

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ['top_comments']

    def get_top_comments(self, obj):
        comments = obj.get_top_level_comments()[:10]
        return CommentSerializer(comments, many=True, context=self.context).data


class CommentWithRepliesSerializer(CommentSerializer):
    """Comment serializer with nested replies"""
    replies = serializers.SerializerMethodField()

    class Meta(CommentSerializer.Meta):
        fields = CommentSerializer.Meta.fields + ['replies']

    def get_replies(self, obj):
        replies = obj.get_replies()[:5]
        return CommentSerializer(replies, many=True, context=self.context).data


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)
    actor_avatar = serializers.ImageField(source='actor.avatar', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'actor', 'actor_name', 'actor_avatar',
            'notification_type', 'post', 'comment', 'project',
            'title', 'message', 'is_read', 'is_sent', 'action_url',
            'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'recipient', 'actor', 'created_at', 'read_at']


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model"""
    reporter_name = serializers.CharField(source='reporter.get_full_name', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'reporter_name', 'reported_post',
            'reported_comment', 'reported_user', 'report_type',
            'description', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'reporter', 'created_at']

    def validate(self, attrs):
        """Validate that at least one reported item is provided"""
        if not any([
            attrs.get('reported_post'),
            attrs.get('reported_comment'),
            attrs.get('reported_user')
        ]):
            raise serializers.ValidationError(
                "At least one of reported_post, reported_comment, or reported_user must be provided"
            )
        return attrs


class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating posts"""

    class Meta:
        model = Post
        fields = [
            'title', 'content', 'content_type', 'image', 'code_snippet',
            'code_language', 'related_project', 'related_module',
            'visibility', 'status'
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        post = Post.objects.create(author=user, **validated_data)
        return post


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments"""

    class Meta:
        model = Comment
        fields = ['content', 'parent_comment']

    def create(self, validated_data):
        user = self.context['request'].user
        post = self.context['post']
        parent_comment = validated_data.get('parent_comment')
        
        comment = Comment.objects.create(
            post=post,
            author=user,
            content=validated_data['content'],
            parent_comment=parent_comment
        )
        return comment

