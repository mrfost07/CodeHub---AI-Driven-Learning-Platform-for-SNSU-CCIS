from django.urls import path
from . import views

app_name = 'learning'

urlpatterns = [
    # Career Paths
    path('career-paths/', views.CareerPathListView.as_view(), name='career-path-list'),
    path('career-paths/<uuid:pk>/', views.CareerPathDetailView.as_view(), name='career-path-detail'),
    path('career-paths/<uuid:pk>/modules/', views.CareerPathModulesView.as_view(), name='career-path-modules'),
    path('career-paths/<uuid:pk>/start/', views.StartCareerPathView.as_view(), name='start-career-path'),
    
    # Learning Modules
    path('modules/', views.LearningModuleListView.as_view(), name='module-list'),
    path('modules/<uuid:pk>/', views.LearningModuleDetailView.as_view(), name='module-detail'),
    path('modules/<uuid:pk>/complete/', views.CompleteModuleView.as_view(), name='complete-module'),
    path('modules/<uuid:pk>/quiz/', views.ModuleQuizView.as_view(), name='module-quiz'),
    
    # Quizzes
    path('quizzes/<uuid:pk>/', views.QuizDetailView.as_view(), name='quiz-detail'),
    path('quizzes/<uuid:pk>/start/', views.QuizStartView.as_view(), name='quiz-start'),
    path('quiz-attempts/<uuid:pk>/submit/', views.QuizSubmitView.as_view(), name='quiz-submit'),
    path('quiz-attempts/', views.QuizAttemptsView.as_view(), name='quiz-attempts'),
    
    # User Progress
    path('progress/', views.UserProgressListView.as_view(), name='user-progress-list'),
    path('progress/<uuid:pk>/', views.UserProgressDetailView.as_view(), name='user-progress-detail'),
]

