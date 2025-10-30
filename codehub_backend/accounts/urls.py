from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, ProfileView, UserDetailView,
    FollowUserView, UserFollowersView, UserFollowingView, SkillListCreateView,
    SkillDetailView, CareerInterestListCreateView, CareerInterestDetailView,
    BadgeListView, BadgeDetailView, UserSkillsView, UserCareerInterestsView,
    UserBadgesView, LeaderboardView, CustomTokenObtainPairView,
    CustomTokenRefreshView
)

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),

    # User profile endpoints
    path('profile/', ProfileView.as_view(), name='profile'),
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<uuid:user_id>/followers/', UserFollowersView.as_view(), name='user_followers'),
    path('users/<uuid:user_id>/following/', UserFollowingView.as_view(), name='user_following'),
    path('users/<uuid:user_id>/follow/', FollowUserView.as_view(), name='follow_user'),

    # Skills endpoints
    path('skills/', SkillListCreateView.as_view(), name='skill_list_create'),
    path('skills/<uuid:pk>/', SkillDetailView.as_view(), name='skill_detail'),
    path('user/skills/', UserSkillsView.as_view(), name='user_skills'),

    # Career interests endpoints
    path('career-interests/', CareerInterestListCreateView.as_view(), name='career_interest_list_create'),
    path('career-interests/<uuid:pk>/', CareerInterestDetailView.as_view(), name='career_interest_detail'),
    path('user/career-interests/', UserCareerInterestsView.as_view(), name='user_career_interests'),

    # Badges endpoints
    path('badges/', BadgeListView.as_view(), name='badge_list'),
    path('badges/<uuid:pk>/', BadgeDetailView.as_view(), name='badge_detail'),
    path('user/badges/', UserBadgesView.as_view(), name='user_badges'),

    # Leaderboard
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]