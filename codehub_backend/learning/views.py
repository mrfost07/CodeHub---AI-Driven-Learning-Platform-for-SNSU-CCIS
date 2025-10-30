from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    CareerPath, LearningModule, Quiz, Question,
    UserProgress, QuizAttempt, Answer
)
from .serializers import (
    CareerPathSerializer, LearningModuleSerializer, QuizSerializer,
    QuestionSerializer, UserProgressSerializer, QuizAttemptSerializer,
    QuizSubmitSerializer
)


class CareerPathListView(generics.ListAPIView):
    """View for listing career paths"""
    serializer_class = CareerPathSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = CareerPath.objects.filter(is_active=True)
        program_type = self.request.query_params.get('program_type', None)
        difficulty = self.request.query_params.get('difficulty', None)
        
        if program_type:
            queryset = queryset.filter(program_type=program_type)
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)
        
        return queryset


class CareerPathDetailView(generics.RetrieveAPIView):
    """View for getting career path details"""
    queryset = CareerPath.objects.filter(is_active=True)
    serializer_class = CareerPathSerializer
    permission_classes = [permissions.AllowAny]


class CareerPathModulesView(generics.ListAPIView):
    """View for getting modules in a career path"""
    serializer_class = LearningModuleSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        career_path_id = self.kwargs['pk']
        return LearningModule.objects.filter(
            career_path_id=career_path_id,
            is_active=True
        ).order_by('module_number')


class LearningModuleListView(generics.ListAPIView):
    """View for listing learning modules"""
    serializer_class = LearningModuleSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = LearningModule.objects.filter(is_active=True)
        career_path = self.request.query_params.get('career_path', None)
        difficulty = self.request.query_params.get('difficulty', None)
        
        if career_path:
            queryset = queryset.filter(career_path_id=career_path)
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)
        
        return queryset.order_by('career_path', 'module_number')


class LearningModuleDetailView(generics.RetrieveAPIView):
    """View for getting learning module details"""
    queryset = LearningModule.objects.filter(is_active=True)
    serializer_class = LearningModuleSerializer
    permission_classes = [permissions.AllowAny]


class QuizDetailView(generics.RetrieveAPIView):
    """View for getting quiz details"""
    queryset = Quiz.objects.filter(is_active=True)
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuizStartView(APIView):
    """View for starting a quiz attempt"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, is_active=True)
        user = request.user

        # Check if user has exceeded max attempts
        attempts_count = QuizAttempt.objects.filter(
            user=user,
            quiz=quiz
        ).count()

        if attempts_count >= quiz.max_attempts:
            return Response(
                {'error': 'Maximum attempts exceeded'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create new attempt
        attempt = QuizAttempt.objects.create(
            user=user,
            quiz=quiz,
            attempt_number=attempts_count + 1,
            score=0
        )

        return Response({
            'message': 'Quiz attempt started',
            'attempt': QuizAttemptSerializer(attempt).data
        }, status=status.HTTP_201_CREATED)


class QuizSubmitView(APIView):
    """View for submitting quiz answers"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        attempt = get_object_or_404(
            QuizAttempt,
            pk=pk,
            user=request.user,
            is_completed=False
        )

        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers_data = serializer.validated_data['answers']

        # Process each answer
        for answer_data in answers_data:
            question_id = answer_data.get('question_id')
            answer_text = answer_data.get('answer_text', '')
            selected_choices = answer_data.get('selected_choices', [])

            question = get_object_or_404(Question, pk=question_id)

            answer = Answer.objects.create(
                attempt=attempt,
                question=question,
                answer_text=answer_text
            )

            if selected_choices:
                answer.selected_choices.set(selected_choices)

            answer.save()

        # Complete the attempt and calculate score
        attempt.is_completed = True
        attempt.completed_at = timezone.now()
        attempt.time_taken = int((attempt.completed_at - attempt.started_at).total_seconds())
        attempt.calculate_score()

        return Response({
            'message': 'Quiz submitted successfully',
            'attempt': QuizAttemptSerializer(attempt).data
        })


class UserProgressListView(generics.ListAPIView):
    """View for listing user's progress"""
    serializer_class = UserProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProgress.objects.filter(user=self.request.user)


class UserProgressDetailView(generics.RetrieveAPIView):
    """View for getting user progress in a specific career path"""
    serializer_class = UserProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        career_path_id = self.kwargs['pk']
        return get_object_or_404(
            UserProgress,
            user=self.request.user,
            career_path_id=career_path_id
        )


class StartCareerPathView(APIView):
    """View for starting a career path"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        career_path = get_object_or_404(CareerPath, pk=pk, is_active=True)
        user = request.user

        # Check if user already started this path
        progress, created = UserProgress.objects.get_or_create(
            user=user,
            career_path=career_path
        )

        if created:
            # Set first module as current
            first_module = career_path.modules.filter(is_active=True).first()
            if first_module:
                progress.current_module = first_module
                progress.save()

            return Response({
                'message': 'Career path started',
                'progress': UserProgressSerializer(progress).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'message': 'Career path already started',
                'progress': UserProgressSerializer(progress).data
            })


class CompleteModuleView(APIView):
    """View for marking a module as completed"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        module = get_object_or_404(LearningModule, pk=pk, is_active=True)
        user = request.user

        # Get or create progress for this career path
        progress, created = UserProgress.objects.get_or_create(
            user=user,
            career_path=module.career_path
        )

        # Mark module as completed
        progress.mark_module_completed(module)

        # Set next module as current
        next_module = LearningModule.objects.filter(
            career_path=module.career_path,
            module_number__gt=module.module_number,
            is_active=True
        ).first()

        if next_module:
            progress.current_module = next_module
            progress.save()

        return Response({
            'message': 'Module completed',
            'progress': UserProgressSerializer(progress).data
        })


class QuizAttemptsView(generics.ListAPIView):
    """View for listing user's quiz attempts"""
    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)


class ModuleQuizView(generics.RetrieveAPIView):
    """View for getting quiz associated with a module"""
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        module_id = self.kwargs['pk']
        module = get_object_or_404(LearningModule, pk=module_id, is_active=True)
        return get_object_or_404(Quiz, module=module, is_active=True)
