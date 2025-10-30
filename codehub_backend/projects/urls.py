from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Projects
    path('', views.ProjectListCreateView.as_view(), name='project-list'),
    path('my-projects/', views.MyProjectsView.as_view(), name='my-projects'),
    path('<uuid:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    
    # Project Members
    path('<uuid:pk>/members/', views.ProjectMembersView.as_view(), name='project-members'),
    path('<uuid:pk>/members/add/', views.AddProjectMemberView.as_view(), name='add-member'),
    path('<uuid:pk>/members/<uuid:user_id>/remove/', views.RemoveProjectMemberView.as_view(), name='remove-member'),
    
    # Project Tasks
    path('<uuid:pk>/tasks/', views.ProjectTasksView.as_view(), name='project-tasks'),
    path('tasks/<uuid:pk>/', views.ProjectTaskDetailView.as_view(), name='task-detail'),
    
    # Project Files
    path('<uuid:pk>/files/', views.ProjectFilesView.as_view(), name='project-files'),
    path('files/<uuid:pk>/', views.ProjectFileDetailView.as_view(), name='file-detail'),
    
    # Code Reviews
    path('<uuid:pk>/code-reviews/', views.ProjectCodeReviewsView.as_view(), name='code-reviews'),
    path('code-reviews/<uuid:pk>/', views.CodeReviewDetailView.as_view(), name='code-review-detail'),
    path('code-reviews/<uuid:pk>/comments/', views.ReviewCommentsView.as_view(), name='review-comments'),
    
    # Project Activities
    path('<uuid:pk>/activities/', views.ProjectActivitiesView.as_view(), name='project-activities'),
]

