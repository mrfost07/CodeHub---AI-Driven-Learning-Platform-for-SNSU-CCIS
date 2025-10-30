from rest_framework import serializers
from .models import (
    ProjectMentorSession, AIMessage, CodeAnalysis,
    LearningRecommendation, ProjectGuidance, AIMentorProfile
)


class AIMessageSerializer(serializers.ModelSerializer):
    """Serializer for AIMessage model"""

    class Meta:
        model = AIMessage
        fields = [
            'id', 'session', 'role', 'content', 'metadata',
            'tokens_used', 'processing_time', 'contains_code',
            'code_language', 'code_snippet', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProjectMentorSessionSerializer(serializers.ModelSerializer):
    """Serializer for ProjectMentorSession model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    messages_count = serializers.SerializerMethodField()
    recent_messages = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMentorSession
        fields = [
            'id', 'user', 'project', 'project_name', 'session_type',
            'code_snippet', 'user_question', 'ai_response',
            'learning_resources', 'status', 'total_messages',
            'ai_model_used', 'tokens_used', 'cost_estimate',
            'temperature', 'max_tokens', 'user_rating', 'feedback_text',
            'created_at', 'updated_at', 'last_activity', 'completed_at',
            'messages_count', 'recent_messages'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'last_activity']

    def get_messages_count(self, obj):
        return obj.get_conversation_length()

    def get_recent_messages(self, obj):
        messages = obj.messages.order_by('-created_at')[:5]
        return AIMessageSerializer(messages, many=True).data


class CodeAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for CodeAnalysis model"""
    issues_count = serializers.SerializerMethodField()
    critical_issues = serializers.SerializerMethodField()

    class Meta:
        model = CodeAnalysis
        fields = [
            'id', 'session', 'code_snippet', 'programming_language',
            'file_name', 'analysis_type', 'findings', 'recommendations',
            'severity_score', 'ai_model_used', 'tokens_used',
            'processing_time', 'status', 'issues_count', 'critical_issues',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']

    def get_issues_count(self, obj):
        return obj.get_issues_count()

    def get_critical_issues(self, obj):
        return obj.get_critical_issues()


class LearningRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for LearningRecommendation model"""
    recommended_career_path_name = serializers.CharField(
        source='recommended_career_path.name',
        read_only=True
    )
    recommended_module_title = serializers.CharField(
        source='recommended_module.title',
        read_only=True
    )

    class Meta:
        model = LearningRecommendation
        fields = [
            'id', 'user', 'session', 'recommendation_type', 'title',
            'description', 'reason', 'recommended_career_path',
            'recommended_career_path_name', 'recommended_module',
            'recommended_module_title', 'recommended_skill',
            'external_url', 'resource_type', 'confidence_score',
            'priority_score', 'is_viewed', 'is_dismissed',
            'user_rating', 'created_at', 'viewed_at', 'expires_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'viewed_at']


class ProjectGuidanceSerializer(serializers.ModelSerializer):
    """Serializer for ProjectGuidance model"""
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = ProjectGuidance
        fields = [
            'id', 'session', 'project', 'project_name', 'guidance_type',
            'title', 'content', 'recommendations', 'implementation_steps',
            'estimated_effort', 'complexity_level', 'is_implemented',
            'user_feedback', 'created_at', 'implemented_at'
        ]
        read_only_fields = ['id', 'created_at', 'implemented_at']


class AIMentorProfileSerializer(serializers.ModelSerializer):
    """Serializer for AIMentorProfile model"""
    can_send_message = serializers.SerializerMethodField()
    messages_remaining = serializers.SerializerMethodField()

    class Meta:
        model = AIMentorProfile
        fields = [
            'id', 'user', 'preferred_ai_model', 'preferred_temperature',
            'preferred_difficulty', 'communication_style',
            'code_explanation_level', 'enable_code_analysis',
            'enable_learning_recommendations', 'enable_project_guidance',
            'daily_message_limit', 'messages_today', 'last_reset_date',
            'can_send_message', 'messages_remaining', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'messages_today', 'last_reset_date', 'created_at', 'updated_at']

    def get_can_send_message(self, obj):
        return obj.can_send_message()

    def get_messages_remaining(self, obj):
        return obj.daily_message_limit - obj.messages_today


class ChatMessageSerializer(serializers.Serializer):
    """Serializer for sending chat messages"""
    message = serializers.CharField(required=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    project_id = serializers.UUIDField(required=True)
    session_type = serializers.ChoiceField(
        choices=['code_review', 'bug_detection', 'project_guidance', 'documentation_help', 'learning_recommendation'],
        default='project_guidance'
    )
    code_snippet = serializers.CharField(required=False, allow_blank=True)
    programming_language = serializers.CharField(required=False, allow_blank=True)


class CodeAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for code analysis requests"""
    code_snippet = serializers.CharField(required=True)
    programming_language = serializers.CharField(required=True)
    analysis_type = serializers.ChoiceField(
        choices=['bug_detection', 'performance', 'security', 'best_practices', 'complexity', 'comprehensive'],
        required=True
    )
    file_name = serializers.CharField(required=False, allow_blank=True)
    project_id = serializers.UUIDField(required=True)

