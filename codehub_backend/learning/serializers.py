from rest_framework import serializers
from .models import (
    CareerPath, LearningModule, Quiz, Question, QuestionChoice,
    UserProgress, QuizAttempt, Answer
)
from accounts.serializers import SkillSerializer


class CareerPathSerializer(serializers.ModelSerializer):
    """Serializer for CareerPath model"""
    required_skills = SkillSerializer(many=True, read_only=True)
    completion_rate = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = CareerPath
        fields = [
            'id', 'name', 'slug', 'description', 'program_type',
            'snsu_ccis_specific', 'difficulty_level', 'estimated_duration',
            'total_modules', 'points_reward', 'required_skills', 'icon',
            'color', 'is_active', 'is_featured', 'completion_rate',
            'average_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_completion_rate(self, obj):
        return obj.get_completion_rate()

    def get_average_rating(self, obj):
        return obj.get_average_rating()


class LearningModuleSerializer(serializers.ModelSerializer):
    """Serializer for LearningModule model"""
    career_path_name = serializers.CharField(source='career_path.name', read_only=True)
    has_quiz = serializers.BooleanField(read_only=True)
    completion_rate = serializers.SerializerMethodField()

    class Meta:
        model = LearningModule
        fields = [
            'id', 'career_path', 'career_path_name', 'is_snsu_ccis_specific',
            'title', 'slug', 'description', 'module_number', 'content_type',
            'video_url', 'video_duration', 'content_text', 'attachments',
            'learning_objectives', 'key_takeaways', 'difficulty_level',
            'estimated_time', 'has_quiz', 'passing_score', 'points_reward',
            'is_active', 'is_preview', 'completion_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_completion_rate(self, obj):
        return obj.get_completion_rate()


class QuestionChoiceSerializer(serializers.ModelSerializer):
    """Serializer for QuestionChoice model"""

    class Meta:
        model = QuestionChoice
        fields = ['id', 'choice_text', 'is_correct', 'explanation', 'order']
        read_only_fields = ['id']


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model"""
    choices = QuestionChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'quiz', 'question_text', 'question_type', 'code_snippet',
            'explanation', 'points', 'difficulty_level', 'order',
            'is_active', 'choices', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class QuizSerializer(serializers.ModelSerializer):
    """Serializer for Quiz model"""
    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'module', 'title', 'description', 'instructions',
            'time_limit', 'max_attempts', 'passing_score',
            'randomize_questions', 'questions_per_attempt', 'is_active',
            'available_from', 'available_until', 'questions',
            'total_questions', 'average_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_questions(self, obj):
        return obj.get_total_questions()

    def get_average_score(self, obj):
        return obj.get_average_score()


class UserProgressSerializer(serializers.ModelSerializer):
    """Serializer for UserProgress model"""
    career_path_name = serializers.CharField(source='career_path.name', read_only=True)
    current_module_title = serializers.CharField(source='current_module.title', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserProgress
        fields = [
            'id', 'user', 'career_path', 'career_path_name',
            'current_module', 'current_module_title', 'modules_completed',
            'total_points_earned', 'is_completed', 'completion_date',
            'progress_percentage', 'started_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'started_at', 'updated_at']

    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()


class AnswerSerializer(serializers.ModelSerializer):
    """Serializer for Answer model"""

    class Meta:
        model = Answer
        fields = [
            'id', 'attempt', 'question', 'answer_text', 'selected_choices',
            'is_correct', 'points_earned', 'answered_at'
        ]
        read_only_fields = ['id', 'is_correct', 'points_earned', 'answered_at']


class QuizAttemptSerializer(serializers.ModelSerializer):
    """Serializer for QuizAttempt model"""
    answers = AnswerSerializer(many=True, read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'user', 'quiz', 'quiz_title', 'started_at',
            'completed_at', 'time_taken', 'score', 'is_passed',
            'is_completed', 'attempt_number', 'answers'
        ]
        read_only_fields = ['id', 'user', 'started_at']


class QuizSubmitSerializer(serializers.Serializer):
    """Serializer for submitting quiz answers"""
    answers = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        )
    )

    def validate_answers(self, value):
        """Validate answers format"""
        for answer in value:
            if 'question_id' not in answer:
                raise serializers.ValidationError("Each answer must have a question_id")
        return value

