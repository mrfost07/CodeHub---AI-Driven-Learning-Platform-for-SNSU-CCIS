from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes as perm_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models

from .models import (
    Post, Comment, PostLike, CommentLike, PostTag, Hashtag,
    Notification, Report
)
from .serializers import (
    PostSerializer, PostDetailSerializer, CommentSerializer,
    CommentWithRepliesSerializer, NotificationSerializer, ReportSerializer,
    PostCreateSerializer, CommentCreateSerializer, PostTagSerializer,
    HashtagSerializer
)


class PostListCreateView(generics.ListCreateAPIView):
    """View for listing and creating posts"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateSerializer
        return PostSerializer

    def get_queryset(self):
        queryset = Post.objects.filter(status='published')
        
        # Apply filters
        content_type = self.request.query_params.get('content_type', None)
        program = self.request.query_params.get('program', None)
        is_official = self.request.query_params.get('is_official', None)
        
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        if program:
            queryset = queryset.filter(program_relevance__in=[program, 'all'])
        if is_official:
            queryset = queryset.filter(is_official=True)
        
        # Order by pinned first, then by date
        return queryset.order_by('-is_pinned', '-published_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for getting, updating, and deleting posts"""
    queryset = Post.objects.all()
    serializer_class = PostDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.increment_views()
        return obj

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        # Check if user is the author
        if obj.author != request.user:
            return Response(
                {'error': 'You can only edit your own posts'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        # Check if user is the author or admin
        if obj.author != request.user and not request.user.role in ['admin', 'moderator']:
            return Response(
                {'error': 'You can only delete your own posts'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class PostLikeView(APIView):
    """View for liking/unliking posts"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk, status='published')
        user = request.user

        if post.is_liked_by(user):
            # Unlike the post
            post.unlike(user)
            return Response({'message': 'Post unliked', 'liked': False})
        else:
            # Like the post
            post.like(user)
            
            # Create notification for post author
            if post.author != user:
                Notification.objects.create(
                    recipient=post.author,
                    actor=user,
                    notification_type='post_like',
                    post=post,
                    title='New Like',
                    message=f'{user.get_full_name()} liked your post'
                )
            
            return Response({'message': 'Post liked', 'liked': True})


class PostCommentsView(generics.ListCreateAPIView):
    """View for listing and creating comments on a post"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentWithRepliesSerializer

    def get_queryset(self):
        post_id = self.kwargs['pk']
        return Comment.objects.filter(
            post_id=post_id,
            parent_comment=None,
            is_active=True
        ).order_by('-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        post_id = self.kwargs['pk']
        context['post'] = get_object_or_404(Post, pk=post_id)
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        
        # Create notification for post author
        post = self.get_serializer_context()['post']
        if post.author != request.user:
            Notification.objects.create(
                recipient=post.author,
                actor=request.user,
                notification_type='comment',
                post=post,
                title='New Comment',
                message=f'{request.user.get_full_name()} commented on your post'
            )
        
        return response


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for getting, updating, and deleting comments"""
    queryset = Comment.objects.filter(is_active=True)
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return Response(
                {'error': 'You can only edit your own comments'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user and not request.user.role in ['admin', 'moderator']:
            return Response(
                {'error': 'You can only delete your own comments'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class CommentLikeView(APIView):
    """View for liking/unliking comments"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk, is_active=True)
        user = request.user

        if comment.is_liked_by(user):
            # Unlike the comment
            comment.unlike(user)
            return Response({'message': 'Comment unliked', 'liked': False})
        else:
            # Like the comment
            comment.like(user)
            
            # Create notification for comment author
            if comment.author != user:
                Notification.objects.create(
                    recipient=comment.author,
                    actor=user,
                    notification_type='comment_like',
                    comment=comment,
                    post=comment.post,
                    title='New Like',
                    message=f'{user.get_full_name()} liked your comment'
                )
            
            return Response({'message': 'Comment liked', 'liked': True})


class NotificationListView(generics.ListAPIView):
    """View for listing user notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        unread_only = self.request.query_params.get('unread', None)
        
        queryset = Notification.objects.filter(recipient=user)
        
        if unread_only == 'true':
            queryset = queryset.filter(is_read=False)
        
        return queryset.order_by('-created_at')[:50]


class NotificationMarkReadView(APIView):
    """View for marking notifications as read"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user
        )
        notification.mark_as_read()
        return Response({'message': 'Notification marked as read'})


class NotificationMarkAllReadView(APIView):
    """View for marking all notifications as read"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        )
        for notification in notifications:
            notification.mark_as_read()
        
        return Response({'message': 'All notifications marked as read'})


class ReportCreateView(generics.CreateAPIView):
    """View for creating reports"""
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class MyPostsView(generics.ListAPIView):
    """View for listing user's own posts"""
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user).order_by('-created_at')


class FeedView(generics.ListAPIView):
    """View for personalized user feed"""
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Get posts from followed users and user's own posts
        following_ids = user.following.values_list('id', flat=True)
        
        queryset = Post.objects.filter(
            status='published'
        ).filter(
            models.Q(author_id__in=following_ids) |
            models.Q(author=user) |
            models.Q(visibility='public')
        ).distinct()
        
        return queryset.order_by('-is_pinned', '-published_at')[:50]


class TrendingHashtagsView(generics.ListAPIView):
    """View for listing trending hashtags"""
    serializer_class = HashtagSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Hashtag.objects.order_by('-usage_count')[:20]


class PostsByHashtagView(generics.ListAPIView):
    """View for listing posts by hashtag"""
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        hashtag = self.kwargs['hashtag']
        return Post.objects.filter(
            hashtags__name=hashtag.lower(),
            status='published'
        ).order_by('-published_at')
