from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # Posts
    path('posts/', views.PostListCreateView.as_view(), name='post-list'),
    path('posts/<uuid:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('posts/<uuid:pk>/like/', views.PostLikeView.as_view(), name='post-like'),
    path('posts/<uuid:pk>/comments/', views.PostCommentsView.as_view(), name='post-comments'),
    path('my-posts/', views.MyPostsView.as_view(), name='my-posts'),
    path('feed/', views.FeedView.as_view(), name='feed'),
    
    # Comments
    path('comments/<uuid:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
    path('comments/<uuid:pk>/like/', views.CommentLikeView.as_view(), name='comment-like'),
    
    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<uuid:pk>/read/', views.NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    
    # Reports
    path('reports/', views.ReportCreateView.as_view(), name='report-create'),
    
    # Hashtags
    path('hashtags/trending/', views.TrendingHashtagsView.as_view(), name='trending-hashtags'),
    path('hashtags/<str:hashtag>/posts/', views.PostsByHashtagView.as_view(), name='posts-by-hashtag'),
]

