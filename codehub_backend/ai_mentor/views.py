from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
import openai
import time

from .models import (
    ProjectMentorSession, AIMessage, CodeAnalysis,
    LearningRecommendation, ProjectGuidance, AIMentorProfile
)
from .serializers import (
    ProjectMentorSessionSerializer, AIMessageSerializer, CodeAnalysisSerializer,
    LearningRecommendationSerializer, ProjectGuidanceSerializer,
    AIMentorProfileSerializer, ChatMessageSerializer, CodeAnalysisRequestSerializer
)
from projects.models import Project


# Set OpenAI API key (should be in environment variables)
openai.api_key = getattr(settings, 'OPENAI_API_KEY', '')


class AIMentorProfileView(generics.RetrieveUpdateAPIView):
    """View for getting and updating AI mentor profile"""
    serializer_class = AIMentorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = AIMentorProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile


class ChatSessionListView(generics.ListAPIView):
    """View for listing chat sessions"""
    serializer_class = ProjectMentorSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        project_id = self.request.query_params.get('project_id', None)
        
        queryset = ProjectMentorSession.objects.filter(user=user)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        return queryset.order_by('-last_activity')


class ChatSessionDetailView(generics.RetrieveAPIView):
    """View for getting chat session details"""
    serializer_class = ProjectMentorSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProjectMentorSession.objects.filter(user=self.request.user)


class SendMessageView(APIView):
    """View for sending messages to AI mentor"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        
        # Get or create AI mentor profile
        profile, created = AIMentorProfile.objects.get_or_create(user=user)
        
        # Check daily limit
        if not profile.can_send_message():
            return Response(
                {'error': 'Daily message limit exceeded'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Get project
        project = get_object_or_404(Project, pk=serializer.validated_data['project_id'])
        
        # Check project access
        if not project.is_member(user) and project.owner != user:
            return Response(
                {'error': 'You do not have access to this project'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get or create session
        session_id = serializer.validated_data.get('session_id')
        if session_id:
            session = get_object_or_404(
                ProjectMentorSession,
                pk=session_id,
                user=user
            )
        else:
            session = ProjectMentorSession.objects.create(
                user=user,
                project=project,
                session_type=serializer.validated_data['session_type'],
                code_snippet=serializer.validated_data.get('code_snippet', ''),
                user_question=serializer.validated_data['message'],
                ai_response='',
                ai_model_used=profile.preferred_ai_model,
                temperature=profile.preferred_temperature
            )

        # Add user message
        user_message_content = serializer.validated_data['message']
        code_snippet = serializer.validated_data.get('code_snippet', '')
        
        if code_snippet:
            user_message_content = f"{user_message_content}\n\nCode:\n```{serializer.validated_data.get('programming_language', '')}\n{code_snippet}\n```"

        session.add_message('user', user_message_content)

        # Call OpenAI API
        try:
            start_time = time.time()
            
            # Build conversation history
            messages = [
                {
                    "role": "system",
                    "content": f"You are an expert programming mentor for SNSU CCIS students. Communication style: {profile.communication_style}. Explanation level: {profile.code_explanation_level}. Provide helpful, educational responses."
                }
            ]
            
            # Add recent messages
            for msg in session.messages.order_by('created_at'):
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

            response = openai.chat.completions.create(
                model=profile.preferred_ai_model,
                messages=messages,
                temperature=float(profile.preferred_temperature),
                max_tokens=session.max_tokens
            )

            ai_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            processing_time = time.time() - start_time

            # Add AI response message
            session.add_message(
                'assistant',
                ai_response,
                {
                    'tokens_used': tokens_used,
                    'processing_time': processing_time
                }
            )

            # Update session
            session.tokens_used += tokens_used
            session.last_activity = timezone.now()
            session.save()

            # Increment profile message count
            profile.increment_message_count()

            return Response({
                'message': 'Message sent successfully',
                'session': ProjectMentorSessionSerializer(session).data,
                'ai_response': ai_response,
                'tokens_used': tokens_used
            })

        except Exception as e:
            return Response(
                {'error': f'AI service error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyzeCodeView(APIView):
    """View for analyzing code with AI"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CodeAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        
        # Get or create AI mentor profile
        profile, created = AIMentorProfile.objects.get_or_create(user=user)
        
        # Check if code analysis is enabled
        if not profile.enable_code_analysis:
            return Response(
                {'error': 'Code analysis is disabled in your profile'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get project
        project = get_object_or_404(Project, pk=serializer.validated_data['project_id'])
        
        # Check project access
        if not project.is_member(user) and project.owner != user:
            return Response(
                {'error': 'You do not have access to this project'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create session
        session = ProjectMentorSession.objects.create(
            user=user,
            project=project,
            session_type='code_review',
            code_snippet=serializer.validated_data['code_snippet'],
            user_question=f"Analyze this code for {serializer.validated_data['analysis_type']}",
            ai_response='',
            ai_model_used=profile.preferred_ai_model
        )

        # Create code analysis
        analysis = CodeAnalysis.objects.create(
            session=session,
            code_snippet=serializer.validated_data['code_snippet'],
            programming_language=serializer.validated_data['programming_language'],
            file_name=serializer.validated_data.get('file_name', ''),
            analysis_type=serializer.validated_data['analysis_type'],
            ai_model_used=profile.preferred_ai_model,
            status='in_progress'
        )

        # Call OpenAI API for code analysis
        try:
            start_time = time.time()

            prompt = f"""Analyze this {serializer.validated_data['programming_language']} code for {serializer.validated_data['analysis_type']}:

```{serializer.validated_data['programming_language']}
{serializer.validated_data['code_snippet']}
```

Provide a detailed analysis in JSON format with:
1. findings: array of issues found (each with: type, severity, description, line_number if applicable)
2. recommendations: array of suggestions for improvement
3. severity_score: overall severity score from 1-10

Return only valid JSON."""

            response = openai.chat.completions.create(
                model=profile.preferred_ai_model,
                messages=[
                    {"role": "system", "content": "You are an expert code reviewer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            ai_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            processing_time = time.time() - start_time

            # Parse AI response (simple version - in production, use proper JSON parsing)
            import json
            try:
                result = json.loads(ai_response)
                analysis.findings = result.get('findings', [])
                analysis.recommendations = result.get('recommendations', [])
                analysis.severity_score = result.get('severity_score', 5)
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON
                analysis.findings = [{'type': 'general', 'severity': 'info', 'description': ai_response}]
                analysis.recommendations = []
                analysis.severity_score = 5

            analysis.tokens_used = tokens_used
            analysis.processing_time = processing_time
            analysis.status = 'completed'
            analysis.completed_at = timezone.now()
            analysis.save()

            # Update session
            session.ai_response = ai_response
            session.tokens_used = tokens_used
            session.save()

            return Response({
                'message': 'Code analysis completed',
                'analysis': CodeAnalysisSerializer(analysis).data
            })

        except Exception as e:
            analysis.status = 'failed'
            analysis.save()
            return Response(
                {'error': f'Code analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LearningRecommendationsView(generics.ListAPIView):
    """View for listing learning recommendations"""
    serializer_class = LearningRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        dismissed = self.request.query_params.get('dismissed', 'false')
        
        queryset = LearningRecommendation.objects.filter(user=user)
        
        if dismissed == 'false':
            queryset = queryset.filter(is_dismissed=False)
        
        return queryset.order_by('-priority_score', '-created_at')


class ProjectGuidanceListView(generics.ListAPIView):
    """View for listing project guidance"""
    serializer_class = ProjectGuidanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id', None)
        
        queryset = ProjectGuidance.objects.filter(session__user=self.request.user)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        return queryset.order_by('-created_at')


class CompleteSessionView(APIView):
    """View for completing a chat session"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(
            ProjectMentorSession,
            pk=pk,
            user=request.user
        )
        
        session.complete_session()
        
        # Optional: Get user rating
        user_rating = request.data.get('user_rating')
        feedback_text = request.data.get('feedback_text', '')
        
        if user_rating:
            session.user_rating = user_rating
            session.feedback_text = feedback_text
            session.save()
        
        return Response({
            'message': 'Session completed',
            'session': ProjectMentorSessionSerializer(session).data
        })
