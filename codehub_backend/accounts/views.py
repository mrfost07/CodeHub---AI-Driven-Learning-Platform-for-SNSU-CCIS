from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import login
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

from .models import User, Skill, CareerInterest, Badge
from .serializers import (
    UserProfileSerializer, UserRegistrationSerializer, UserUpdateSerializer,
    LoginSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer,
    FollowUserSerializer, UserStatsSerializer, SkillSerializer,
    CareerInterestSerializer, BadgeSerializer
)


class RegisterView(generics.CreateAPIView):
    """View for user registration"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        print("=== REGISTRATION REQUEST DATA ===")
        print(f"Request data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
        
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        return Response({
            'message': 'User registered successfully',
            'user': UserProfileSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """View for user login"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Log the user in
        login(request, user)

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        return Response({
            'message': 'Login successful',
            'user': UserProfileSerializer(user).data,
            'tokens': tokens
        })


class LogoutView(APIView):
    """View for user logout"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logout successful'})
        except Exception:
            return Response({'message': 'Logout successful'})


class ProfileView(generics.RetrieveUpdateAPIView):
    """View for getting and updating user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = UserUpdateSerializer(
            instance,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            'message': 'Profile updated successfully',
            'user': UserProfileSerializer(user).data
        })


class UserDetailView(generics.RetrieveAPIView):
    """View for getting public user details"""
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserStatsSerializer
    permission_classes = [permissions.AllowAny]


class FollowUserView(APIView):
    """View for following/unfollowing users"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        serializer = FollowUserSerializer(
            data={'user_id': user_id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        target_user = get_object_or_404(User, id=user_id)
        current_user = request.user

        if current_user.is_following(target_user):
            current_user.unfollow(target_user)
            return Response({'message': 'User unfollowed', 'following': False})

        current_user.follow(target_user)
        return Response({'message': 'User followed', 'following': True})


class UserFollowersView(generics.ListAPIView):
    """View for getting user's followers"""
    serializer_class = UserStatsSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, is_active=True)
        return user.followers.filter(is_active=True)


class UserFollowingView(generics.ListAPIView):
    """View for getting users that a user is following"""
    serializer_class = UserStatsSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, is_active=True)
        return user.following.filter(is_active=True)


class SkillListCreateView(generics.ListCreateAPIView):
    """View for listing and creating skills"""
    queryset = Skill.objects.filter(is_active=True)
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class SkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for getting, updating, and deleting skills"""
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated]


class CareerInterestListCreateView(generics.ListCreateAPIView):
    """View for listing and creating career interests"""
    queryset = CareerInterest.objects.filter(is_active=True)
    serializer_class = CareerInterestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class CareerInterestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for getting, updating, and deleting career interests"""
    queryset = CareerInterest.objects.all()
    serializer_class = CareerInterestSerializer
    permission_classes = [permissions.IsAuthenticated]


class BadgeListView(generics.ListAPIView):
    """View for listing badges"""
    queryset = Badge.objects.filter(is_active=True)
    serializer_class = BadgeSerializer
    permission_classes = [permissions.AllowAny]


class BadgeDetailView(generics.RetrieveAPIView):
    """View for getting badge details"""
    queryset = Badge.objects.filter(is_active=True)
    serializer_class = BadgeSerializer
    permission_classes = [permissions.AllowAny]


class UserSkillsView(APIView):
    """View for managing user's skills"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's skills"""
        user = request.user
        skills = user.skills.filter(is_active=True)
        serializer = SkillSerializer(skills, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Add skill to user"""
        skill_id = request.data.get('skill_id')
        try:
            skill = Skill.objects.get(id=skill_id, is_active=True)
            user = request.user
            user.skills.add(skill)
            return Response({
                'message': 'Skill added successfully',
                'skill': SkillSerializer(skill).data
            })
        except Skill.DoesNotExist:
            return Response(
                {'error': 'Skill not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request):
        """Remove skill from user"""
        skill_id = request.data.get('skill_id')
        try:
            skill = Skill.objects.get(id=skill_id)
            user = request.user
            user.skills.remove(skill)
            return Response({'message': 'Skill removed successfully'})
        except Skill.DoesNotExist:
            return Response(
                {'error': 'Skill not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserCareerInterestsView(APIView):
    """View for managing user's career interests"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's career interests"""
        user = request.user
        interests = user.career_interests.filter(is_active=True)
        serializer = CareerInterestSerializer(interests, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Add career interest to user"""
        interest_id = request.data.get('interest_id')
        try:
            interest = CareerInterest.objects.get(id=interest_id, is_active=True)
            user = request.user
            user.career_interests.add(interest)
            return Response({
                'message': 'Career interest added successfully',
                'interest': CareerInterestSerializer(interest).data
            })
        except CareerInterest.DoesNotExist:
            return Response(
                {'error': 'Career interest not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request):
        """Remove career interest from user"""
        interest_id = request.data.get('interest_id')
        try:
            interest = CareerInterest.objects.get(id=interest_id)
            user = request.user
            user.career_interests.remove(interest)
            return Response({'message': 'Career interest removed successfully'})
        except CareerInterest.DoesNotExist:
            return Response(
                {'error': 'Career interest not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserBadgesView(generics.ListAPIView):
    """View for getting user's earned badges"""
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return user.badges.filter(is_active=True)


class LeaderboardView(generics.ListAPIView):
    """View for getting user leaderboard"""
    serializer_class = UserStatsSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Get top users by points and level
        return User.objects.filter(is_active=True).order_by(
            '-points', '-level', 'username'
        )[:50]


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view with additional user data"""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            user = self.user
            response.data['user'] = UserProfileSerializer(user).data

        return response


class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh view"""
    pass
