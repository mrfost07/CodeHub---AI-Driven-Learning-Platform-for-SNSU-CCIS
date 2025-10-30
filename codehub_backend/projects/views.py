from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models

from .models import (
    Project, ProjectMembership, ProjectTask, TaskLabel, ProjectTag,
    ProjectFile, CodeReview, ReviewAssignment, ReviewComment, ProjectActivity
)
from .serializers import (
    ProjectSerializer, ProjectDetailSerializer, ProjectMembershipSerializer,
    ProjectTaskSerializer, TaskLabelSerializer, ProjectTagSerializer,
    ProjectFileSerializer, CodeReviewSerializer, ReviewCommentSerializer,
    ProjectActivitySerializer
)


class ProjectListCreateView(generics.ListCreateAPIView):
    """View for listing and creating projects"""
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Project.objects.all()

        # Filter by visibility
        if not user.is_authenticated:
            queryset = queryset.filter(visibility='public')
        else:
            # Show public projects, user's own projects, and projects they're a member of
            queryset = queryset.filter(
                models.Q(visibility='public') |
                models.Q(owner=user) |
                models.Q(team_members=user)
            ).distinct()

        # Apply additional filters
        status_filter = self.request.query_params.get('status', None)
        project_type = self.request.query_params.get('project_type', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if project_type:
            queryset = queryset.filter(project_type=project_type)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        # Add owner as admin member
        ProjectMembership.objects.create(
            project=project,
            user=self.request.user,
            role='admin'
        )
        # Log activity
        ProjectActivity.objects.create(
            project=project,
            user=self.request.user,
            activity_type='project_created',
            description=f'{self.request.user.get_full_name()} created the project'
        )


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for getting, updating, and deleting projects"""
    queryset = Project.objects.all()
    serializer_class = ProjectDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        
        # Check visibility permissions
        if obj.visibility == 'private' and not obj.is_member(user) and obj.owner != user:
            self.permission_denied(self.request, message='You do not have access to this project')
        
        return obj


class ProjectMembersView(generics.ListAPIView):
    """View for listing project members"""
    serializer_class = ProjectMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs['pk']
        return ProjectMembership.objects.filter(
            project_id=project_id,
            is_active=True
        )


class AddProjectMemberView(APIView):
    """View for adding a member to a project"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        
        # Check if user can administer project
        if not project.can_user_administer(request.user):
            return Response(
                {'error': 'You do not have permission to add members'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        role = request.data.get('role', 'member')

        from accounts.models import User
        member = get_object_or_404(User, id=user_id)

        membership, created = ProjectMembership.objects.get_or_create(
            project=project,
            user=member,
            defaults={
                'role': role,
                'invited_by': request.user
            }
        )

        if created:
            # Log activity
            ProjectActivity.objects.create(
                project=project,
                user=request.user,
                activity_type='member_added',
                description=f'{request.user.get_full_name()} added {member.get_full_name()} to the project',
                metadata={'member_id': str(member.id), 'role': role}
            )

            return Response({
                'message': 'Member added successfully',
                'membership': ProjectMembershipSerializer(membership).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'message': 'User is already a member'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RemoveProjectMemberView(APIView):
    """View for removing a member from a project"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, user_id):
        project = get_object_or_404(Project, pk=pk)
        
        # Check if user can administer project
        if not project.can_user_administer(request.user):
            return Response(
                {'error': 'You do not have permission to remove members'},
                status=status.HTTP_403_FORBIDDEN
            )

        from accounts.models import User
        member = get_object_or_404(User, id=user_id)

        # Cannot remove owner
        if member == project.owner:
            return Response(
                {'error': 'Cannot remove project owner'},
                status=status.HTTP_400_BAD_REQUEST
            )

        membership = get_object_or_404(
            ProjectMembership,
            project=project,
            user=member
        )
        membership.delete()

        # Log activity
        ProjectActivity.objects.create(
            project=project,
            user=request.user,
            activity_type='member_removed',
            description=f'{request.user.get_full_name()} removed {member.get_full_name()} from the project'
        )

        return Response({'message': 'Member removed successfully'})


class ProjectTasksView(generics.ListCreateAPIView):
    """View for listing and creating project tasks"""
    serializer_class = ProjectTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs['pk']
        queryset = ProjectTask.objects.filter(project_id=project_id)
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('order')

    def perform_create(self, serializer):
        project_id = self.kwargs['pk']
        project = get_object_or_404(Project, pk=project_id)
        
        # Check if user can edit project
        if not project.can_user_edit(self.request.user):
            self.permission_denied(self.request, message='You do not have permission to create tasks')
        
        task = serializer.save(project=project)
        
        # Log activity
        ProjectActivity.objects.create(
            project=project,
            user=self.request.user,
            activity_type='task_created',
            description=f'{self.request.user.get_full_name()} created task: {task.title}'
        )


class ProjectTaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for getting, updating, and deleting project tasks"""
    queryset = ProjectTask.objects.all()
    serializer_class = ProjectTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        task = serializer.save()
        
        # Log activity
        ProjectActivity.objects.create(
            project=task.project,
            user=self.request.user,
            activity_type='task_updated',
            description=f'{self.request.user.get_full_name()} updated task: {task.title}'
        )


class ProjectFilesView(generics.ListCreateAPIView):
    """View for listing and uploading project files"""
    serializer_class = ProjectFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs['pk']
        return ProjectFile.objects.filter(
            project_id=project_id,
            is_active=True
        ).order_by('-uploaded_at')

    def perform_create(self, serializer):
        project_id = self.kwargs['pk']
        project = get_object_or_404(Project, pk=project_id)
        
        # Check if user can edit project
        if not project.can_user_edit(self.request.user):
            self.permission_denied(self.request, message='You do not have permission to upload files')
        
        file = serializer.save(
            project=project,
            uploaded_by=self.request.user
        )
        
        # Log activity
        ProjectActivity.objects.create(
            project=project,
            user=self.request.user,
            activity_type='file_uploaded',
            description=f'{self.request.user.get_full_name()} uploaded file: {file.filename}'
        )


class ProjectFileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for getting, updating, and deleting project files"""
    queryset = ProjectFile.objects.all()
    serializer_class = ProjectFileSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProjectCodeReviewsView(generics.ListCreateAPIView):
    """View for listing and creating code reviews"""
    serializer_class = CodeReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs['pk']
        return CodeReview.objects.filter(project_id=project_id).order_by('-created_at')

    def perform_create(self, serializer):
        project_id = self.kwargs['pk']
        project = get_object_or_404(Project, pk=project_id)
        
        review = serializer.save(
            project=project,
            author=self.request.user
        )
        
        # Log activity
        ProjectActivity.objects.create(
            project=project,
            user=self.request.user,
            activity_type='review_created',
            description=f'{self.request.user.get_full_name()} created code review: {review.title}'
        )


class CodeReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for getting, updating, and deleting code reviews"""
    queryset = CodeReview.objects.all()
    serializer_class = CodeReviewSerializer
    permission_classes = [permissions.IsAuthenticated]


class ReviewCommentsView(generics.ListCreateAPIView):
    """View for listing and creating review comments"""
    serializer_class = ReviewCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        review_id = self.kwargs['pk']
        return ReviewComment.objects.filter(
            review_id=review_id,
            is_active=True
        ).order_by('created_at')

    def perform_create(self, serializer):
        review_id = self.kwargs['pk']
        review = get_object_or_404(CodeReview, pk=review_id)
        
        serializer.save(
            review=review,
            author=self.request.user
        )


class ProjectActivitiesView(generics.ListAPIView):
    """View for listing project activities"""
    serializer_class = ProjectActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs['pk']
        return ProjectActivity.objects.filter(project_id=project_id).order_by('-created_at')[:50]


class MyProjectsView(generics.ListAPIView):
    """View for listing user's own projects"""
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Project.objects.filter(owner=user).order_by('-created_at')
