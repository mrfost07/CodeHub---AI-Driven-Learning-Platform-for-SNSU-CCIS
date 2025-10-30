from django.urls import path
from . import views

app_name = 'ai_mentor'

urlpatterns = [
    # AI Mentor Profile
    path('profile/', views.AIMentorProfileView.as_view(), name='mentor-profile'),
    
    # Chat Sessions
    path('sessions/', views.ChatSessionListView.as_view(), name='session-list'),
    path('sessions/<uuid:pk>/', views.ChatSessionDetailView.as_view(), name='session-detail'),
    path('sessions/<uuid:pk>/complete/', views.CompleteSessionView.as_view(), name='complete-session'),
    path('send-message/', views.SendMessageView.as_view(), name='send-message'),
    
    # Code Analysis
    path('analyze-code/', views.AnalyzeCodeView.as_view(), name='analyze-code'),
    
    # Learning Recommendations
    path('recommendations/', views.LearningRecommendationsView.as_view(), name='recommendations'),
    
    # Project Guidance
    path('guidance/', views.ProjectGuidanceListView.as_view(), name='guidance-list'),
]

